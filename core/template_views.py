from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from .models import Doctor, Patient, Visit, Test, Medication, FileUpload, AIChatMessage, AIPrompt
from django.shortcuts import get_object_or_404
from django import forms
import random
import string
from django.urls import reverse
from datetime import datetime
from .utils import get_patient_context as utils_get_patient_context, format_chat_messages, get_ai_stream_response, query_ollama_chat, get_detailed_patient_data
from functools import wraps
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import traceback
from typing import List, Dict
import json

# First define the decorators
def doctor_required(view_func):
    @login_required(login_url='doctor_login')
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'doctor'):
            return redirect('doctor_login')
        return view_func(request, *args, **kwargs)
    return wrapper

def patient_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'patient'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# Form classes
class DoctorRegistrationForm(forms.Form):
    name = forms.CharField(max_length=255)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    specialization = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=15)
    hospital = forms.CharField(max_length=255, required=False)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

# Helper functions
def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# View functions
def doctor_login(request):
    if request.user.is_authenticated and hasattr(request.user, 'doctor'):
        return redirect('doctor_dashboard')
    
    next_url = request.GET.get('next', 'doctor_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(username=email, password=password)
        if user is not None and hasattr(user, 'doctor'):
            login(request, user)
            return redirect(next_url)
    return render(request, 'core/doctor/login.html')

@doctor_required
def doctor_dashboard(request):
    patients = Patient.objects.filter(doctor=request.user.doctor)
    context = {
        'patients': patients
    }
    return render(request, 'core/doctor/dashboard.html', context)

# Patient Views
def patient_login(request):
    if request.user.is_authenticated and hasattr(request.user, 'patient'):
        return redirect('patient_dashboard')
        
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        
        try:
            # Debug messages
            print(f"Attempting login with phone: {phone}")
            
            User = get_user_model()
            try:
                user = User.objects.get(username=phone)
                print(f"Found user: {user.username}")
                print(f"Is patient: {hasattr(user, 'patient')}")
            except User.DoesNotExist:
                print("User not found")
                return render(request, 'core/patient/login.html')
            
            authenticated_user = authenticate(username=phone, password=password)
            print(f"Authentication result: {authenticated_user is not None}")
            
            if authenticated_user is not None:
                print(f"Has patient attr: {hasattr(authenticated_user, 'patient')}")
                
            if authenticated_user is not None and hasattr(authenticated_user, 'patient'):
                login(request, authenticated_user)
                return redirect('patient_dashboard')
            else:
                return render(request, 'core/patient/login.html')
        except Exception as e:
            print(f"Login error: {str(e)}")
    
    return render(request, 'core/patient/login.html')

@patient_required
def patient_dashboard(request):
    visits = Visit.objects.filter(patient=request.user.patient).order_by('-date_of_visit')
    medications = Medication.objects.filter(visit__patient=request.user.patient).order_by('-visit__date_of_visit')[:5]
    tests = Test.objects.filter(visit__patient=request.user.patient).order_by('-visit__date_of_visit')[:5]
    
    context = {
        'visits': visits,
        'recent_medications': medications,
        'recent_tests': tests
    }
    return render(request, 'core/patient/dashboard.html', context)

@patient_required
def patient_medications(request):
    medications = Medication.objects.filter(
        visit__patient=request.user.patient
    ).order_by('-visit__date_of_visit')
    
    context = {
        'medications': medications
    }
    return render(request, 'core/patient/medications.html', context)

@patient_required
def patient_tests(request):
    tests = Test.objects.filter(
        visit__patient=request.user.patient
    ).order_by('-visit__date_of_visit')
    
    context = {
        'tests': tests
    }
    return render(request, 'core/patient/tests.html', context)

@patient_required
def patient_files(request):
    # Get all files for the patient, ordered by upload date
    files = FileUpload.objects.filter(
        visit__patient=request.user.patient
    ).select_related('visit', 'visit__doctor').order_by('-uploaded_at')
    
    context = {
        'files': files
    }
    return render(request, 'core/patient/files.html', context)

@patient_required
def patient_visit_detail(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id, patient=request.user.patient)
    medications = Medication.objects.filter(visit=visit)
    tests = Test.objects.filter(visit=visit)
    files = FileUpload.objects.filter(visit=visit)
    
    context = {
        'visit': visit,
        'medications': medications,
        'tests': tests,
        'files': files
    }
    return render(request, 'core/patient/visit_detail.html', context)

def logout_view(request):
    # Determine user type before logout
    is_doctor = hasattr(request.user, 'doctor')
    is_patient = hasattr(request.user, 'patient')
    
    logout(request)
    
    # Redirect based on user type
    if is_doctor:
        return redirect('doctor_login')
    elif is_patient:
        return redirect('patient_login')
    else:
        return redirect('doctor_login')  # Default redirect

# Add this view function
def doctor_register(request):
    if request.method == 'POST':
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            User = get_user_model()
            
            # Check if email already exists
            if User.objects.filter(username=form.cleaned_data['email']).exists():
                return render(request, 'core/doctor/register.html', {'form': form})
            
            # Create user
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                is_doctor=True
            )
            
            # Create doctor profile
            doctor = Doctor.objects.create(
                user=user,
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                specialization=form.cleaned_data['specialization'],
                phone=form.cleaned_data['phone'],
                hospital=form.cleaned_data['hospital']
            )
            
            return redirect('doctor_login')
    else:
        form = DoctorRegistrationForm()
    
    return render(request, 'core/doctor/register.html', {'form': form})

# Add this function to generate random passwords
def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Add the patient creation view
@doctor_required
def doctor_patient_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        
        password = generate_password()
        
        try:
            User = get_user_model()
            # Check if user already exists
            if User.objects.filter(username=phone).exists():
                return render(request, 'core/doctor/patient_add.html')
            
            # Create user with is_patient flag
            user = User.objects.create_user(
                username=phone,
                password=password,
                is_patient=True
            )
            
            # Create patient profile
            patient = Patient.objects.create(
                user=user,
                doctor=request.user.doctor,
                name=name,
                date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d').date(),
                gender=gender,
                phone=phone,
                address=address,
                password=password  # Store the plain password temporarily for display
            )
            
            return redirect('doctor_dashboard')
            
        except Exception as e:
            return render(request, 'core/doctor/patient_add.html')
            
    return render(request, 'core/doctor/patient_add.html')

# Add patient detail view
@doctor_required
def doctor_patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user.doctor)
    visits = Visit.objects.filter(patient=patient).order_by('-date_of_visit')
    files = FileUpload.objects.filter(visit__patient=patient).order_by('-uploaded_at')
    
    context = {
        'patient': patient,
        'visits': visits,
        'files': files
    }
    return render(request, 'core/doctor/patient_detail.html', context)

@doctor_required
def doctor_visit_add(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user.doctor)
    
    if request.method == 'POST':
        try:
            # Create the visit
            visit = Visit.objects.create(
                patient=patient,
                doctor=request.user.doctor,
                date_of_visit=datetime.strptime(request.POST.get('date_of_visit'), '%Y-%m-%d').date(),
                diagnosis=request.POST.get('diagnosis'),
                treatment_plan=request.POST.get('treatment_plan'),
                notes=request.POST.get('notes', '')
            )
            
            # Handle medications
            medication_names = request.POST.getlist('medication_name[]')
            medication_reasons = request.POST.getlist('medication_reason[]')
            medication_instructions = request.POST.getlist('medication_instructions[]')
            medication_missed_instructions = request.POST.getlist('medication_missed_instructions[]')
            
            for i in range(len(medication_names)):
                if medication_names[i]:
                    Medication.objects.create(
                        visit=visit,
                        medication_name=medication_names[i],
                        reason=medication_reasons[i],
                        instructions=medication_instructions[i],
                        missed_dose_instructions=medication_missed_instructions[i]
                    )
            
            # Handle tests
            test_names = request.POST.getlist('test_name[]')
            test_regions = request.POST.getlist('test_region[]')
            test_reasons = request.POST.getlist('test_reason[]')
            
            for i in range(len(test_names)):
                if test_names[i]:
                    Test.objects.create(
                        visit=visit,
                        test_name=test_names[i],
                        region=test_regions[i],
                        reason=test_reasons[i]
                    )
            
            # Handle file uploads
            files = request.FILES.getlist('files[]')
            for file in files:
                FileUpload.objects.create(
                    visit=visit,
                    file_path=file,
                    description=request.POST.get('file_description', '')
                )
            
            return redirect('doctor_patient_detail', patient_id=patient.id)
            
        except Exception as e:
            return render(request, 'core/doctor/visit_add.html')
    
    context = {
        'patient': patient
    }
    return render(request, 'core/doctor/visit_add.html', context)

@doctor_required
def doctor_visit_detail(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id, doctor=request.user.doctor)
    medications = Medication.objects.filter(visit=visit)
    tests = Test.objects.filter(visit=visit)
    files = FileUpload.objects.filter(visit=visit)
    
    context = {
        'visit': visit,
        'medications': medications,
        'tests': tests,
        'files': files
    }
    return render(request, 'core/doctor/visit_detail.html', context)

@doctor_required
def doctor_patient_delete(request, patient_id):
    if request.method == 'POST':
        patient = get_object_or_404(Patient, id=patient_id, doctor=request.user.doctor)
        user = patient.user
        patient.delete()
        user.delete()
    return redirect('doctor_dashboard')

@doctor_required
def doctor_patient_update(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user.doctor)
    
    if request.method == 'POST':
        try:
            patient.name = request.POST.get('name')
            patient.date_of_birth = datetime.strptime(request.POST.get('date_of_birth'), '%Y-%m-%d').date()
            patient.gender = request.POST.get('gender')
            patient.phone = request.POST.get('phone')
            patient.address = request.POST.get('address')
            patient.save()
        except Exception as e:
            return render(request, 'core/doctor/patient_detail.html')
            
    return redirect('doctor_patient_detail', patient_id=patient_id)

@doctor_required
def doctor_visit_delete(request, visit_id):
    if request.method == 'POST':
        visit = get_object_or_404(Visit, id=visit_id, doctor=request.user.doctor)
        patient_id = visit.patient.id
        visit.delete()
    return redirect('doctor_patient_detail', patient_id=patient_id)

@doctor_required
def doctor_file_upload(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, doctor=request.user.doctor)
    
    if request.method == 'POST':
        try:
            file = request.FILES.get('file')
            description = request.POST.get('description', '')
            
            # Create a new visit for the file if no visit is specified
            visit = Visit.objects.create(
                patient=patient,
                doctor=request.user.doctor,
                date_of_visit=datetime.now().date(),
                diagnosis="File Upload",
                treatment_plan="Document Upload Only"
            )
            
            FileUpload.objects.create(
                visit=visit,
                file_path=file,
                description=description
            )
        except Exception as e:
            return render(request, 'core/doctor/patient_detail.html')
            
    return redirect('doctor_patient_detail', patient_id=patient_id)

@doctor_required
def doctor_file_delete(request, file_id):
    if request.method == 'POST':
        file = get_object_or_404(FileUpload, id=file_id, visit__patient__doctor=request.user.doctor)
        patient_id = file.visit.patient.id
        file.delete()
    return redirect('doctor_patient_detail', patient_id=patient_id)

@patient_required
def patient_ai_chat(request):
    """AI chat view for patients - using regular sync responses"""
    patient = request.user.patient
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Handle reset chat
    if request.method == 'POST' and 'reset_chat' in request.POST:
        AIChatMessage.objects.filter(patient=patient).delete()
        
        # Create a welcome message
        greeting = "Hello! I'm your AI health assistant. How can I help you today?"
        AIChatMessage.objects.create(
            patient=patient,
            message=greeting,
            is_ai=True
        )
        return redirect('patient_ai_chat')
    
    # Handle new message
    elif request.method == 'POST' and 'message' in request.POST:
        user_message = request.POST.get('message', '').strip()
        
        if user_message:
            # Save user message
            AIChatMessage.objects.create(
                patient=patient,
                message=user_message,
                is_ai=False
            )
            
            try:
                # Get patient context
                system_context = get_patient_context(patient)
                
                # Create system message with comprehensive instructions and dynamic patient data
                system_message = {
                    "role": "system",
                    "content": f"""You are a healthcare assistant speaking directly to {patient.name} about their own health. There is no ambiguity - you are ALWAYS talking to the patient themselves.

CORE APPROACH:
- ALWAYS address {patient.name} directly as "you"
- ALWAYS discuss their health using "your" (e.g., "your blood sugar")
- NEVER use third-person references like "the patient should"
- NEVER switch between perspectives - you are consistently talking to {patient.name}
- Think of this as a face-to-face conversation between a healthcare worker and {patient.name}

DO NOT:
- Include instructional text or notes to yourself
- Use meta-commentary in parentheses
- Use placeholders like "[insert time]"
- Create formal section headers
- Mention "having access to records" or "medical data"
- Reveal you're an AI or mention being "trained"
- Give technical explanations of how you work
- Talk about the patient in the third person EVER
- Include disclaimers about limitations

DO:
- Speak naturally like a human healthcare professional
- Address {patient.name} by name occasionally
- Focus on answering their specific questions directly
- Keep responses conversational and warm
- Use contractions and casual language
- Format information in a readable but natural way
- Adapt your level of detail to match their questions
- Show appropriate emotion and personality

EXAMPLES OF GOOD RESPONSES:
- "Your blood sugar was 126 in your last test, {patient.name}. That's a bit high, so keep an eye on your carb intake this week."
- "Take your Metformin with breakfast and dinner. If you forget a dose, take it when you remember unless it's almost time for the next one."
- "I see your cholesterol has improved since last time! Whatever you're doing seems to be working well."

PATIENT'S MEDICAL INFORMATION:
{get_detailed_patient_data(patient)}

Remember, you are ALWAYS speaking directly to {patient.name} in a natural, human conversation about their health."""
                }
                
                # Get previous messages to provide context
                chat_history = AIChatMessage.objects.filter(
                    patient=patient
                ).order_by('created_at')
                
                # Format messages for Ollama
                formatted_messages = [system_message]
                
                # Add chat history (up to 10 messages to avoid context length issues)
                for msg in chat_history.order_by('-created_at')[:10]:
                    formatted_messages.append({
                        "role": "assistant" if msg.is_ai else "user",
                        "content": msg.message
                    })
                
                # Get AI response from Ollama
                ai_response = query_ollama_chat(formatted_messages)
                
                # Save AI response
                AIChatMessage.objects.create(
                    patient=patient,
                    message=ai_response,
                    is_ai=True
                )
                
                # If this is an AJAX request, return JSON response
                if is_ajax:
                    response_data = {
                        'success': True,
                        'message': ai_response
                    }
                    return HttpResponse(
                        json.dumps(response_data),
                        content_type='application/json'
                    )
                
                # Otherwise redirect to the chat page
                return redirect('patient_ai_chat')
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"AI Chat Error: {str(e)}\n{error_details}")
                
                # In case of error, provide a fallback message
                error_message = f"Sorry, I'm having trouble processing your request: {str(e)}"
                AIChatMessage.objects.create(
                    patient=patient,
                    message=error_message,
                    is_ai=True
                )
                
                # If this is an AJAX request, return JSON response with error
                if is_ajax:
                    response_data = {
                        'success': False,
                        'error': str(e),
                        'message': error_message
                    }
                    return HttpResponse(
                        json.dumps(response_data),
                        content_type='application/json'
                    )
                
                # Otherwise redirect to the chat page
                return redirect('patient_ai_chat')
    
    # Get messages for display
    messages = AIChatMessage.objects.filter(patient=patient).order_by('created_at')
    
    # Check if Ollama is available directly
    try:
        import requests
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        ollama_available = response.status_code == 200
    except Exception:
        ollama_available = False
    
    context = {
        'messages': messages,
        'ollama_available': ollama_available
    }
    
    return render(request, 'core/patient/ai_chat.html', context)

def get_patient_context(patient):
    """Generate comprehensive context from patient data for AI, using the utils function"""
    # Use the comprehensive function from utils.py
    return utils_get_patient_context(patient)