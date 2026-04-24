from typing import List, Dict, Generator, Any, Optional, Tuple
import requests
import json
import time
from django.conf import settings
from .models import Visit, Medication, FileUpload, Test, AIPrompt, AIChatMessage
from django.db import models
import os
import base64
from pathlib import Path
import mimetypes
import PyPDF2
import io
from datetime import date

# Groq API configuration (loaded from Django settings / environment)
GROQ_API_ENDPOINT = getattr(settings, 'GROQ_API_BASE', 'https://api.groq.com/openai/v1')
GROQ_API_KEY = getattr(settings, 'GROQ_API_KEY', '')
GROQ_MODEL = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')
REQUEST_TIMEOUT = 15  # seconds for normal requests
DOCUMENT_TIMEOUT = 60  # seconds for document processing


def build_patient_refs(patient) -> Dict[str, Dict[str, Any]]:
    """Build a lookup map for AI citation pills.

    Returns a dict keyed by "<kind>:<id>" with `label`, `subtitle`, `url`, `kind`
    and `id`. Used both for client-side pill rendering and for teaching the
    model which reference tokens it may emit.
    """
    from django.urls import reverse  # local import to avoid AppRegistryNotReady

    def _fmt_date(d):
        if not d:
            return ""
        try:
            return d.strftime('%b %-d, %Y')
        except (ValueError, AttributeError):
            try:
                return d.strftime('%b %d, %Y')
            except Exception:
                return str(d)

    refs: Dict[str, Dict[str, Any]] = {}

    visits = Visit.objects.filter(patient=patient).order_by('-date_of_visit')
    for v in visits:
        date_label = _fmt_date(v.date_of_visit)
        doctor_name = (
            v.doctor.name if getattr(v.doctor, 'name', None)
            else getattr(v.doctor.user, 'get_full_name', lambda: '')()
        )
        refs[f"visit:{v.id}"] = {
            "kind": "visit",
            "id": v.id,
            "label": f"Visit · {date_label}",
            "subtitle": f"Dr. {doctor_name}" if doctor_name else "",
            "url": reverse('patient_visit_detail', args=[v.id]),
            "date": date_label,
            "doctor": doctor_name or "",
            "diagnosis": v.diagnosis or "",
            "treatment": v.treatment_plan or "",
            "notes": v.notes or "",
        }

    meds_url = reverse('patient_medications')
    for m in Medication.objects.filter(visit__patient=patient).select_related('visit'):
        name = m.medication_name if hasattr(m, 'medication_name') else getattr(m, 'name', 'Medication')
        refs[f"med:{m.id}"] = {
            "kind": "med",
            "id": m.id,
            "label": name,
            "subtitle": f"Prescribed {m.visit.date_of_visit.strftime('%b %Y')}" if m.visit_id else "",
            "url": f"{meds_url}#med-{m.id}",
            "reason": getattr(m, 'reason', '') or '',
            "instructions": getattr(m, 'instructions', '') or '',
            "missed": getattr(m, 'missed_dose_instructions', '') or '',
            "visit_date": _fmt_date(m.visit.date_of_visit) if m.visit_id else '',
        }

    tests_url = reverse('patient_tests')
    for t in Test.objects.filter(visit__patient=patient).select_related('visit'):
        subtitle_bits = []
        if t.region:
            subtitle_bits.append(t.region)
        if t.visit_id:
            subtitle_bits.append(t.visit.date_of_visit.strftime('%b %Y'))
        try:
            result_file_url = t.result_file.url if t.result_file else ''
            result_file_name = t.result_file.name.split('/')[-1] if t.result_file else ''
        except Exception:
            result_file_url = ''
            result_file_name = ''
        refs[f"test:{t.id}"] = {
            "kind": "test",
            "id": t.id,
            "label": t.test_name,
            "subtitle": " · ".join(subtitle_bits),
            "url": f"{tests_url}#test-{t.id}",
            "region": t.region or "",
            "reason": t.reason or "",
            "result": t.result or "",
            "result_at": _fmt_date(getattr(t, 'result_added_at', None)),
            "result_file_url": result_file_url,
            "result_file_name": result_file_name,
            "visit_date": _fmt_date(t.visit.date_of_visit) if t.visit_id else '',
        }

    for f in FileUpload.objects.filter(visit__patient=patient).select_related('visit'):
        fname = f.file_path.name.split('/')[-1] if f.file_path else f"file-{f.id}"
        try:
            url = f.file_path.url
        except Exception:
            url = ''
        refs[f"file:{f.id}"] = {
            "kind": "file",
            "id": f.id,
            "label": fname,
            "subtitle": f.description or (f.visit.date_of_visit.strftime('%b %Y') if f.visit_id else ''),
            "url": url,
            "mime": (mimetypes.guess_type(fname)[0] or ''),
        }

    # Test result files too (attached directly to a Test)
    for t in Test.objects.filter(visit__patient=patient).exclude(result_file='').exclude(result_file=None).select_related('visit'):
        if not t.result_file:
            continue
        fname = t.result_file.name.split('/')[-1]
        try:
            url = t.result_file.url
        except Exception:
            url = ''
        refs[f"testfile:{t.id}"] = {
            "kind": "file",
            "id": t.id,
            "label": fname,
            "subtitle": f"Report · {t.test_name}",
            "url": url,
            "mime": (mimetypes.guess_type(fname)[0] or ''),
        }

    return refs


def get_patient_context(patient) -> str:
    """Generate comprehensive context from all available patient data including visits, tests, medications and files with document analysis"""
    context = f"""PATIENT INFORMATION:
Name: {patient.user.get_full_name() if hasattr(patient.user, 'get_full_name') else patient.name}
ID: {patient.id}
Gender: {patient.gender}
Blood Group: {patient.blood_group if hasattr(patient, 'blood_group') else 'Not recorded'}
Age: {patient.age if hasattr(patient, 'age') else 'Not recorded'}
Contact: {patient.contact_number if hasattr(patient, 'contact_number') else patient.phone}
Address: {patient.address if patient.address else 'Not recorded'}
"""

    # Get all visits ordered by most recent first
    visits = Visit.objects.filter(patient=patient).order_by('-date_of_visit')

    # Track all files to process them later
    all_files = []

    if visits.exists():
        context += "\n\nMEDICAL HISTORY:\n"
        for i, visit in enumerate(visits):
            context += f"\n--- VISIT #{i+1}: {visit.date_of_visit}  (cite as [[visit:{visit.id}]]) ---"
            context += f"\nAttending Doctor: {visit.doctor.name if hasattr(visit.doctor, 'name') else visit.doctor.user.get_full_name()}"
            context += f"\nDiagnosis: {visit.diagnosis}"
            context += f"\nTreatment Plan: {visit.treatment_plan}"

            if visit.notes:
                context += f"\nAdditional Notes: {visit.notes}"

            # Get medications for this visit
            medications = Medication.objects.filter(visit=visit)
            if medications.exists():
                context += "\n\nPrescribed Medications:"
                for med in medications:
                    med_name = med.medication_name if hasattr(
                        med, 'medication_name') else med.name
                    dosage = med.dosage if hasattr(
                        med, 'dosage') else 'Not specified'
                    frequency = med.frequency if hasattr(
                        med, 'frequency') else 'Not specified'

                    context += f"\n- {med_name} [[med:{med.id}]]"
                    if hasattr(med, 'dosage') and hasattr(med, 'frequency'):
                        context += f" ({dosage}, {frequency})"
                    if hasattr(med, 'reason') and med.reason:
                        context += f" - For: {med.reason}"
                    if hasattr(med, 'instructions') and med.instructions:
                        context += f"\n  Instructions: {med.instructions}"
                    if hasattr(med, 'missed_dose_instructions') and med.missed_dose_instructions:
                        context += f"\n  Missed Dose: {med.missed_dose_instructions}"

            # Get tests for this visit
            tests = Test.objects.filter(visit=visit)
            if tests.exists():
                context += "\n\nOrdered Tests:"
                for test in tests:
                    context += f"\n- {test.test_name} [[test:{test.id}]]"
                    if test.region:
                        context += f" (Region: {test.region})"
                    if test.reason:
                        context += f" - Reason: {test.reason}"
                    if test.result:
                        context += f"\n  Result: {test.result}"
                    elif test.result_file:
                        context += f"\n  Result: see attached report file [[testfile:{test.id}]]"
                    else:
                        context += "\n  Result: Pending"
                    if test.result_file:
                        # Queue the test's own result file for document extraction
                        class _TestFileProxy:
                            def __init__(self, test):
                                self.file_path = test.result_file
                                self.description = f"Lab report for {test.test_name}"
                                self.uploaded_at = test.result_added_at or visit.date_of_visit
                                self.visit = test.visit
                        all_files.append(_TestFileProxy(test))

            # Get files for this visit
            files = FileUpload.objects.filter(visit=visit)
            if files.exists():
                context += "\n\nUploaded Files:"
                for file in files:
                    file_name = file.file_path.name.split('/')[-1]
                    context += f"\n- {file_name} [[file:{file.id}]]"
                    if file.description:
                        context += f" - {file.description}"
                    context += f" (Uploaded: {file.uploaded_at.strftime('%Y-%m-%d')})"
                    # Add to all files for processing
                    all_files.append(file)

            # Add AI prompts if any
            prompts = AIPrompt.objects.filter(visit=visit)
            if prompts.exists():
                context += "\n\nClinician Notes for AI:"
                for prompt in prompts:
                    if prompt.prompt:
                        context += f"\n- {prompt.prompt}"

    # Add summary information at the end
    context += "\n\nSUMMARY STATS:"
    context += f"\nTotal Visits: {visits.count()}"
    context += f"\nMost Recent Visit: {visits.first().date_of_visit if visits.exists() else 'None'}"

    # Count unique conditions from diagnoses for a simple "conditions list"
    all_diagnoses = [v.diagnosis for v in visits]
    unique_conditions = set()
    for diag in all_diagnoses:
        for condition in diag.split(','):
            unique_conditions.add(condition.strip())

    if unique_conditions:
        context += "\nRecorded Conditions:"
        for condition in unique_conditions:
            context += f"\n- {condition}"

    # Process document contents if files exist
    if all_files:
        file_contents = get_file_contents(all_files)
        if file_contents:
            context += "\n\nDOCUMENT CONTENTS AND ANALYSIS:"
            for filename, file_data in file_contents.items():
                context += f"\n\n--- FILE: {filename} ---"
                context += f"\nDescription: {file_data['description']}"
                context += f"\nUploaded: {file_data['upload_date']}"
                context += f"\nFile Type: {file_data['file_type']}"
                context += f"\nSize: {file_data['size']} bytes"
                context += f"\nVisit Date: {file_data['visit_date']}"
                context += f"\nProcessed Using: {file_data['model_used']} (took {file_data['processing_time']})"
                context += f"\n\nEXTRACTED CONTENT:\n{file_data['content']}"

    return context


def is_groq_available() -> bool:
    """Check if Groq API is available"""
    try:
        response = requests.get(
            f"{GROQ_API_ENDPOINT}/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=2
        )
        return response.status_code == 200
    except:
        return False


def get_fallback_response(query: str) -> str:
    """Generate a fallback response when API is unavailable"""
    return "I apologize, but I'm currently experiencing technical difficulties. Please try again later."


def get_ai_stream_response(messages: List[Dict]) -> Generator[str, None, None]:
    """Get streaming response from Groq API (skips the preflight ping — the
    stream call itself is the source of truth for availability).
    """
    try:
        response = requests.post(
            f"{GROQ_API_ENDPOINT}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "stream": True,
                "temperature": 0.4,
                "top_p": 0.9,
                "max_tokens": 800
            },
            stream=True,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            yield f"Sorry, the AI service returned an error ({response.status_code}). Please try again."
            return

        for line in response.iter_lines():
            if line:
                if line.startswith(b"data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data != b"[DONE]":
                        try:
                            json_response = json.loads(data)
                            if "choices" in json_response and len(json_response["choices"]) > 0:
                                delta = json_response["choices"][0].get(
                                    "delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue

    except requests.exceptions.ConnectionError:
        yield "I apologize, but I'm having trouble connecting to the AI service."
    except requests.exceptions.Timeout:
        yield "I apologize, but the AI service is taking too long to respond."
    except Exception as e:
        yield f"I apologize, but I'm having trouble with the AI service. Error: {str(e)}"


def format_chat_messages(patient, user_message: str = None, history: Optional[List[Dict[str, Any]]] = None) -> List[Dict]:
    """Format messages for the chat API including patient context.

    `history` is an optional list of prior turns in the form
    [{"role": "user"|"assistant", "content": "..."}, ...].
    """
    first_name = (patient.name or "").split(" ")[0] or "there"
    doctor_name = ""
    if getattr(patient, "doctor", None):
        doctor_name = f"Dr. {patient.doctor.name}"

    system_message = {
        "role": "system",
        "content": f"""You are the Swajarnika health assistant — a friendly, plain-spoken helper that talks to {first_name} about their own medical records.

HOW TO TALK
- Write like a calm, knowledgeable friend. Short sentences, one idea at a time. Conversational, not clinical.
- Address the patient by first name ({first_name}) when it feels natural. Don't overdo it.
- Prefer plain prose. Only use bullet points when you're genuinely listing 3+ things (medications, steps). Never emit markdown headings (##) in short replies — this is a chat.
- Keep replies tight: 2–5 short sentences for most questions. Expand only if the patient asks for detail.
- Match the patient's energy. If they ask a quick question, answer quick. If they want to understand something, explain kindly.

WHAT YOU KNOW
- Everything in the PATIENT RECORD below: visits, diagnoses, prescribed medications (with reasons, schedules and missed-dose guidance), ordered tests, test results, and text extracted from any uploaded reports.
- You do NOT know anything that isn't in that record. If the patient asks about something you can't see, say so honestly — e.g. "I don't see a record of that in your file."

WHAT TO DO
- Answer questions about their own visits, medications, tests, and reports — grounded in the record. Quote specific numbers or doctor's notes when relevant (e.g. "your HbA1c from March was 8.6%").
- For missed doses, read the instructions the doctor left and follow them exactly. Do not invent rules.
- For general health questions adjacent to their condition (lifestyle, diet, warning signs to watch for), give a short, sensible answer and mention when to check with {doctor_name or "their doctor"}.
- For anything requiring a new prescription, dose change, or diagnosis — don't play doctor. Say clearly that only {doctor_name or "their treating doctor"} can make that call, and suggest they message or book a visit.
- For red-flag symptoms (chest pain, severe breathlessness, sudden weakness, heavy bleeding, high fever in a small child, etc.), tell them clearly to seek urgent care immediately.

WHAT NOT TO DO
- No medical disclaimers longer than one short sentence. No "I am an AI" preambles unless directly asked.
- Don't refuse in a robotic way. If something is out of scope, say what you can help with instead.
- Don't hallucinate dosages, drug interactions, or test values that aren't in the record.
- Don't mention "system prompt", "instructions", "roleplay", or internal implementation.

CITATIONS (IMPORTANT)
- When you refer to a specific visit, medication, test, or uploaded report from the record, embed its reference token inline RIGHT AFTER the thing you're talking about. The tokens render as clickable pills for the patient.
- Formats you may emit (and ONLY these):
    [[visit:<id>]]     — a specific visit
    [[med:<id>]]       — a specific prescribed medication
    [[test:<id>]]      — a specific ordered test
    [[file:<id>]]      — an uploaded document
    [[testfile:<id>]]  — a lab report file attached to a test
- Use ONLY ids that appear in the PATIENT RECORD below. Never invent an id. If you are unsure, don't cite.
- NEVER emit a token with an empty or placeholder id. `[[file:]]`, `[[med:?]]`, `[[visit:unknown]]` are all forbidden. If you don't know the exact id, write the name plainly without any token.
- Do not invent filenames either. If you mention a document, use the exact filename from the PATIENT RECORD or don't name a file at all.
- Place tokens inline, not in a separate "References:" list. E.g.:
    "Your HbA1c on [[visit:12]] was 8.6% — see the full report [[testfile:21]]."
    "You're currently on Metformin [[med:45]] twice daily."
- Don't cite the same token twice in one sentence. Don't cite for generic facts that aren't tied to a specific record entry.
- Keep the surrounding sentence natural. The token is in addition to, not a replacement for, a natural description.
- INSIDE TABLE CELLS: emit ONLY the token for the cell's primary entity — do not also write the name. The pill renders with the name already. E.g. a medication column cell should be just `[[med:45]]`, not `Metformin [[med:45]]`. Outside tables, write the name followed by the token as usual.

FORMATTING & STRUCTURE
- Use Markdown tables for anything schedule- or list-shaped with 3+ attributes per item (medication schedules, test panels, visit summaries). One row per item.
- Keep column headers short and single-word when possible: use `Dose` not `Dosage`, `When` not `Time of day`, `Freq.` not `Frequency`. Avoid headers longer than ~8 characters; they will be truncated to a single line.
- Keep cell contents short. Put long explanations in a paragraph *below* the table, not inside cells.
- Prefer tables over bullet lists when comparing items side-by-side. Prefer short paragraphs over tables for narrative answers.
- Do not wrap tables in code fences. Do not use HTML tags; Markdown only.

PATIENT RECORD
{get_patient_context(patient)}
"""
    }

    messages = [system_message]

    if history:
        for turn in history:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    if user_message:
        messages.append({
            "role": "user",
            "content": user_message
        })

    return messages


def query_groq_chat(messages: List[Dict[str, Any]]) -> str:
    """Get response from Groq chat API"""
    try:
        if not is_groq_available():
            return get_fallback_response("")

        response = requests.post(
            f"{GROQ_API_ENDPOINT}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 1024
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            return f"Sorry, there was an error connecting to the AI service. Status code: {response.status_code}"

        response_data = response.json()

        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            return "I don't have an answer for that question."

    except Exception as e:
        return f"Sorry, an error occurred while generating a response: {str(e)}"


def is_vision_available() -> bool:
    """Check if vision capabilities are available"""
    # Akash API handles vision models automatically
    return True


def get_best_vision_model() -> Optional[str]:
    """Get the best available vision model for document processing"""
    # Akash API handles vision models automatically
    return "gpt-4-vision-preview"


def extract_text_from_pdf(pdf_path: str) -> Tuple[str, str]:
    """Extract text from a PDF file using PyPDF2"""
    try:
        # Open the PDF file in binary mode
        with open(pdf_path, 'rb') as pdf_file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Get the number of pages
            num_pages = len(pdf_reader.pages)

            # Extract text from each page
            text = ""
            for page_num in range(num_pages):
                # Get the page object
                page = pdf_reader.pages[page_num]

                # Extract text from the page
                page_text = page.extract_text()

                # Add a page marker and the extracted text
                text += f"\n----- Page {page_num + 1} -----\n"
                text += page_text

            # If we didn't get any meaningful text, return an error
            if not text.strip() or len(text.strip()) < 50:
                return f"PDF text extraction yielded insufficient text. The PDF may be scanned or contain images rather than text.", "PyPDF2_insufficient"

            return text, "PyPDF2"
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}", "PyPDF2_failed"


def extract_text_from_file(file_path: str) -> Tuple[str, str]:
    """
    Extract text from a document file:
    - PDF files: Use PyPDF2
    - Text files: Direct reading
    - Other files: Use vision model

    Returns a tuple of (extracted_text, model_used)
    """
    # Get the absolute file path
    full_path = os.path.join(
        settings.MEDIA_ROOT, file_path.replace('/media/', ''))

    # Skip if file doesn't exist
    if not os.path.exists(full_path):
        return f"File not found at {full_path}", "none"

    # Get file type
    file_type, _ = mimetypes.guess_type(full_path)

    # If it's a PDF file, use PyPDF2
    if file_type == 'application/pdf' or file_path.lower().endswith('.pdf'):
        text, method = extract_text_from_pdf(full_path)

        # If PyPDF2 failed or yielded insufficient text, try with vision model as fallback
        if method.endswith('_failed') or method.endswith('_insufficient'):
            print(
                f"PyPDF2 extraction issue: {text}. Falling back to vision model.")
            vision_model = get_best_vision_model()
            if vision_model:
                # Fall back to vision AI for this PDF
                fallback_text, fallback_method = extract_text_with_vision_model(
                    full_path, file_type, vision_model)
                return fallback_text, f"{method} -> {fallback_method}"
        return text, method

    # If it's a text file, just read it directly
    if file_type and file_type.startswith('text/'):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read(), "text_reader"
        except UnicodeDecodeError:
            # If UTF-8 fails, try other encodings
            try:
                with open(full_path, 'r', encoding='latin-1') as f:
                    return f.read(), "text_reader"
            except Exception as e:
                return f"Error reading text file: {str(e)}", "none"
        except Exception as e:
            return f"Error reading text file: {str(e)}", "none"

    # For other file types (images, etc.), use vision model
    vision_model = get_best_vision_model()
    if not vision_model:
        return "No vision models available for document processing.", "none"

    return extract_text_with_vision_model(full_path, file_type, vision_model)


def extract_text_with_vision_model(file_path: str, file_type: Optional[str], vision_model: str) -> Tuple[str, str]:
    """Extract text from a file using vision AI model"""
    try:
        # Read file and encode in base64
        with open(file_path, 'rb') as file:
            file_content = file.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')

        # Format message for vision model
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract and transcribe all the text content from this document, preserving the layout structure as much as possible. This is a medical document, so please pay attention to medical terminology and ensure accuracy."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{file_type or 'application/octet-stream'};base64,{base64_content}"
                        }
                    }
                ]
            }
        ]

        # Call Groq API (vision-capable model)
        response = requests.post(
            f"{GROQ_API_ENDPOINT}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.1
            },
            timeout=DOCUMENT_TIMEOUT
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"], "groq-vision"
        else:
            return f"Failed to extract text: API responded with code {response.status_code}", "vision_failed"

    except Exception as e:
        return f"Error extracting document text: {str(e)}", "vision_error"


def analyze_document_file(file_upload) -> Dict[str, Any]:
    """Analyze a document file and return structured information about it"""
    # Get basic file info
    file_name = os.path.basename(file_upload.file_path.name)
    file_url = file_upload.file_path.url
    file_type, _ = mimetypes.guess_type(file_url)

    # Extract text from the document
    start_time = time.time()
    extracted_text, model_used = extract_text_from_file(file_url)
    processing_time = time.time() - start_time

    # Create a structured response
    return {
        "file_name": file_name,
        "description": file_upload.description or "No description provided",
        "url": file_url,
        "content": extracted_text,
        "upload_date": file_upload.uploaded_at.strftime('%Y-%m-%d'),
        "file_type": file_type or "Unknown",
        "model_used": model_used,
        "processing_time": f"{processing_time:.2f} seconds",
        "size": os.path.getsize(os.path.join(settings.MEDIA_ROOT, file_upload.file_path.name.replace('/media/', ''))),
        "visit_date": file_upload.visit.date_of_visit.strftime('%Y-%m-%d') if file_upload.visit else "Unknown"
    }


def get_file_contents(files):
    """Process a list of files and extract their text content"""
    file_contents = {}

    # Store temporary messages about document reading
    reading_messages = {}

    # First pass: create placeholders to show document reading status
    for file in files:
        file_name = os.path.basename(file.file_path.name)
        reading_messages[file_name] = f"Reading file: {file_name}... This may take a moment."

    # Create or update a temporary message in the database
    if files and len(files) > 0:
        # Get the patient from the first file's visit
        patient = files[0].visit.patient

        # Create a temporary message indicating document processing
        file_count = len(files)
        temp_message = f"I'm analyzing {file_count} document{'s' if file_count > 1 else ''}... This may take a moment."

        # Check if there's already a temporary message
        temp_chat = AIChatMessage.objects.filter(
            patient=patient,
            message__startswith="I'm analyzing",
            is_ai=True
        ).order_by('-created_at').first()

        if temp_chat:
            # Update existing message
            temp_chat.message = temp_message
            temp_chat.save()
        else:
            # Create new message
            AIChatMessage.objects.create(
                patient=patient,
                message=temp_message,
                is_ai=True
            )

    # Second pass: actually process each file
    for file in files:
        file_name = os.path.basename(file.file_path.name)

        # Get detailed document analysis
        file_analysis = analyze_document_file(file)

        # Save the extracted text and analysis
        file_contents[file_name] = file_analysis

    # If we created a temporary message, update or delete it
    if files and len(files) > 0:
        # Get the patient from the first file's visit
        patient = files[0].visit.patient

        # Find the temporary message
        temp_chat = AIChatMessage.objects.filter(
            patient=patient,
            message__startswith="I'm analyzing",
            is_ai=True
        ).order_by('-created_at').first()

        if temp_chat:
            # Delete the temporary message - we'll include this info in the main context
            temp_chat.delete()

    return file_contents


def check_pdf_library_installed() -> bool:
    """Check if PyPDF2 is properly installed"""
    try:
        import PyPDF2
        return True
    except ImportError:
        return False


def get_patient_pdf_text(patient_id):
    """Get combined text from all PDFs uploaded by patient"""
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    if not os.path.exists(upload_dir):
        return ""

    pdf_texts = []

    for filename in os.listdir(upload_dir):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(upload_dir, filename)
            text, _ = extract_text_from_pdf(pdf_path)
            if text and not text.startswith("Error"):
                pdf_texts.append(text)

    return "\n\n".join(pdf_texts)


def format_pdf_context(pdf_text):
    """Format PDF text for AI context"""
    if not pdf_text:
        return ""
    return f"""
    Here is relevant information from the user's documents:
    {pdf_text[:8000]}  # Limit to 8000 chars to avoid context overflow
    """


def get_detailed_patient_data(patient):
    """
    Generate comprehensive and detailed patient data from all available records.
    This function pulls data from all related models to create a complete picture.
    """
    data_sections = []

    # Basic patient information
    patient_info = [
        f"Name: {patient.name}",
        f"Age: {calculate_age(patient.date_of_birth) if hasattr(patient, 'date_of_birth') else 'Not recorded'}",
        f"Gender: {patient.gender if hasattr(patient, 'gender') else 'Not recorded'}",
        f"Phone: {patient.phone}"
    ]
    data_sections.append("BASIC INFORMATION:\n- " + "\n- ".join(patient_info))

    # Get all visits with details
    visits = Visit.objects.filter(patient=patient).order_by('-date_of_visit')
    if visits.exists():
        visit_details = []
        for visit in visits:
            visit_info = [
                f"Date: {visit.date_of_visit.strftime('%B %d, %Y')}",
                f"Doctor: Dr. {visit.doctor.name}",
                f"Diagnosis: {visit.diagnosis}",
                f"Treatment Plan: {visit.treatment_plan}"
            ]
            if visit.notes:
                visit_info.append(f"Additional Notes: {visit.notes}")
            visit_details.append("- Visit on " + visit.date_of_visit.strftime(
                '%B %d, %Y') + ":\n  * " + "\n  * ".join(visit_info))

        data_sections.append("MEDICAL VISITS:\n" + "\n".join(visit_details))

    # Get all medications
    medications = Medication.objects.filter(
        visit__patient=patient).order_by('-visit__date_of_visit')
    if medications.exists():
        med_list = []
        for med in medications:
            med_info = [
                f"Name: {med.medication_name}",
                f"Prescribed: {med.visit.date_of_visit.strftime('%B %d, %Y')}",
                f"Instructions: {med.instructions}",
                f"Missed Dose Instructions: {med.missed_dose_instructions}",
                f"Reason: {med.reason}"
            ]
            med_list.append("- " + med.medication_name +
                            ":\n  * " + "\n  * ".join(med_info))

        data_sections.append("MEDICATIONS:\n" + "\n".join(med_list))

    # Get all tests
    tests = Test.objects.filter(
        visit__patient=patient).order_by('-visit__date_of_visit')
    if tests.exists():
        test_list = []
        for test in tests:
            test_info = [
                f"Name: {test.test_name}",
                f"Date: {test.visit.date_of_visit.strftime('%B %d, %Y')}",
                f"Region: {test.region if test.region else 'Not specified'}"
            ]
            if test.result:
                test_info.append(f"Result: {test.result}")
            else:
                test_info.append("Result: Pending")
            test_info.append(f"Reason: {test.reason}")

            test_list.append("- " + test.test_name +
                             ":\n  * " + "\n  * ".join(test_info))

        data_sections.append("TESTS AND RESULTS:\n" + "\n".join(test_list))

    # Get all files and their content if available
    files = FileUpload.objects.filter(visit__patient=patient)
    if files.exists():
        file_list = []
        for file in files:
            file_info = [
                f"Name: {os.path.basename(file.file_path.name)}",
                f"Visit Date: {file.visit.date_of_visit.strftime('%B %d, %Y')}",
                f"Uploaded: {file.uploaded_at.strftime('%B %d, %Y')}"
            ]
            if file.description:
                file_info.append(f"Description: {file.description}")

            file_list.append(
                "- " + os.path.basename(file.file_path.name) + ":\n  * " + "\n  * ".join(file_info))

        data_sections.append("MEDICAL FILES:\n" + "\n".join(file_list))

    # Return the combined data sections
    return "\n\n".join(data_sections)


def calculate_age(birth_date):
    """Calculate age from birthdate"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
