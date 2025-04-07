from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
import openai
from django.contrib.auth import authenticate, login, logout
from .serializers import DoctorRegisterSerializer, PatientRegisterSerializer, VisitSerializer, FileUploadSerializer
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import os
from django.conf import settings
from .models import AIChatMessage, FileUpload, Visit, Patient, Doctor, AIPrompt
from .utils import format_chat_messages
import tempfile
import uuid
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
import random
import string
import requests
User = get_user_model()

openai.api_key = "sk-lRtbEbMz_nah_M3s-64K1g"
openai.base_url = "https://chatapi.akash.network/api/v1"


def make_random_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


class DoctorRegisterView(APIView):
    def post(self, request):
        serializer = DoctorRegisterSerializer(data=request.data)
        if serializer.is_valid():
            doctor = serializer.save()
            return Response({'id': doctor.id, 'message': 'Doctor registered successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DoctorLoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(username=email, password=password)
        if user is not None and getattr(user, 'is_doctor', False):
            login(request, user)
            return Response({'message': 'Login successful'})
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


class PatientRegisterView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def post(self, request):
        # Ensure the user is a doctor
        if not hasattr(request.user, 'doctor'):
            return Response({'error': 'Only doctors can register patients.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        # Generate a secure random password for the patient
        password = make_random_password()
        # You may pass this to the patient in response
        data['password'] = password
        if User.objects.filter(username=data['phone']).exists():
            return Response({'error': 'A user with this phone number already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create a user for the patient
        user = User.objects.create_user(
            username=data['phone'],
            password=password,
            is_patient=True
        )
        serializer = PatientRegisterSerializer(data=data)
        if serializer.is_valid():
            patient = serializer.save(
                user=user, doctor=request.user.doctor, password=password)
            return Response({'patient_id': patient.id, 'generated_password': password}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def create_ai_prompt(visit):
    # Gather diagnosis and medications details
    medications = Medication.objects.filter(visit=visit)
    prompt_text = f"Diagnosis: {visit.diagnosis}\nTreatment: {visit.treatment_plan}\n"
    for med in medications:
        prompt_text += f"Medication: {med.medication_name} - {med.instructions} (Missed dose: {med.missed_dose_instructions})\n"
    AIPrompt.objects.create(patient=visit.patient,
                            visit=visit, prompt=prompt_text)


class VisitCreateView(APIView):
    def post(self, request):
        serializer = VisitSerializer(data=request.data)
        if serializer.is_valid():
            visit = serializer.save()
            create_ai_prompt(visit)  # update AI prompt table
            return Response({'visit_id': visit.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'File uploaded successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AIInteractView(APIView):
    def post(self, request):
        patient_id = request.data.get('patient_id')
        question = request.data.get('question')

        try:
            # Get the patient
            patient = Patient.objects.get(id=patient_id)

            # Format messages for Akash API
            messages = format_chat_messages(patient, question)

            # Get AI response from Akash API
            answer = query_akash_chat(messages)

            return Response({'answer': answer})
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PatientLoginView(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')

        try:
            user = User.objects.get(username=phone)
        except User.DoesNotExist:
            return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)

        user = authenticate(username=phone, password=password)
        if user is not None and hasattr(user, 'patient'):
            login(request, user)
            return Response({'message': 'Login successful', 'patient_id': user.patient.id}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)


class PatientProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            patient = request.user.patient
            serializer = PatientRegisterSerializer(patient)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response({'error': 'Not a patient'}, status=status.HTTP_403_FORBIDDEN)


# class ChatAPIView(APIView):
#     def post(self, request):
#         message = request.data.get('message')
#         if not message:
#             return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Use the Akash API directly instead of OpenAI client
#             response = requests.post(
#                 "https://chatapi.akash.network/api/v1/chat/completions/",
#                 headers={
#                     "Authorization": "Bearer sk-kSOuRSNOgj1XmRUm6rk48A",
#                     "Content-Type": "application/json"
#                 },
#                 json={
#                     "model": "gpt-4",
#                     "messages": [{"role": "user", "content": message}],
#                     "temperature": 0.7,
#                     "max_tokens": 1024
#                 },
#                 timeout=15
#             )

#             if response.status_code == 200:
#                 response_data = response.json()
#                 print(response_data)  # Debugging line to check the response
#                 answer = response_data['choices'][0]['message']['content']
#                 return Response({'message': answer}, status=status.HTTP_200_OK)
#             else:
#                 return Response({'error': f"API error: {response.status_code}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatAPIView(APIView):
    def post(self, request):
        message = request.data.get('message')
        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get the patient from the request
            # This depends on your authentication system
            patient = request.user.patient  # Adjust based on your model relationships

            # Format messages as a doctor using the utils function
            # This already includes the patient context
            messages = format_chat_messages(patient, message)

            payload = {
                "model": "Meta-Llama-3-1-8B-Instruct-FP8",
                "messages": messages,  # Use the formatted messages from utils
                "temperature": 0.7,
                "max_tokens": 1024
            }

            headers = {
                "Authorization": "Bearer sk-lRtbEbMz_nah_M3s-64K1g",
                "Content-Type": "application/json"
            }

            response = requests.post(
                "https://chatapi.akash.network/api/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=20
            )

            if response.status_code == 200:
                response_data = response.json()
                ai_reply = response_data['choices'][0]['message']['content']

                # Save the conversation to the database if needed
                # AIChatMessage.objects.create(
                #     patient=patient,
                #     message=ai_reply,
                #     is_ai=True
                # )

                return Response({'message': ai_reply}, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': f"API Error: {response.status_code}",
                    'details': response.text
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except requests.exceptions.Timeout:
            return Response({'error': 'The request timed out.'}, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


# @require_POST
# @csrf_exempt
# def chat_api(request):
#     """API endpoint for chat interactions with Akash API"""
#     try:
#         # Check if user is authenticated and is a patient
#         if not request.user.is_authenticated or not hasattr(request.user, 'patient'):
#             return JsonResponse({'error': 'Authentication required'}, status=401)

#         patient = request.user.patient
#         message = request.POST.get('message', '').strip()
#         uploaded_file = request.FILES.get('file')

#         # Save user message
#         if message:
#             AIChatMessage.objects.create(
#                 patient=patient,
#                 message=message,
#                 is_ai=False
#             )
#         elif uploaded_file and not message:
#             # If only a file was uploaded without a message, create a default message
#             message = f"I'm sending you this file: {uploaded_file.name}"
#             AIChatMessage.objects.create(
#                 patient=patient,
#                 message=message,
#                 is_ai=False
#             )

#         # Handle file upload if present
#         file_content = None
#         if uploaded_file:
#             # Create a temporary file
#             temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
#             os.makedirs(temp_dir, exist_ok=True)

#             # Generate a unique filename
#             file_extension = os.path.splitext(uploaded_file.name)[1]
#             temp_filename = f"{uuid.uuid4()}{file_extension}"
#             temp_filepath = os.path.join(temp_dir, temp_filename)

#             # Save the uploaded file
#             with open(temp_filepath, 'wb+') as destination:
#                 for chunk in uploaded_file.chunks():
#                     destination.write(chunk)

#             # Extract text from the file
#             file_content, extraction_method = extract_text_from_file(
#                 temp_filepath)

#             # Create a visit for the file if needed
#             visit = Visit.objects.filter(
#                 patient=patient).order_by('-date_of_visit').first()
#             if not visit:
#                 # Create a new visit for the file
#                 from datetime import datetime
#                 visit = Visit.objects.create(
#                     patient=patient,
#                     doctor=patient.doctor,
#                     date_of_visit=datetime.now().date(),
#                     diagnosis="File Upload via Chat",
#                     treatment_plan="Document Upload Only"
#                 )

#             # Save the file to the database
#             file_upload = FileUpload.objects.create(
#                 visit=visit,
#                 file_path=uploaded_file,
#                 description=f"Uploaded via chat: {uploaded_file.name}"
#             )

#             # Add file content to the message if extracted successfully
#             if file_content and not file_content.startswith("Error"):
#                 message += f"\n\nThe file contains the following text:\n{file_content}"

#         # Format messages for Akash API
#         formatted_messages = format_chat_messages(patient, message)

#         # Get AI response from Akash API
#         ai_response = query_akash_chat(formatted_messages)

#         # Save AI response
#         AIChatMessage.objects.create(
#             patient=patient,
#             message=ai_response,
#             is_ai=True
#         )

#         # Return response
#         return JsonResponse({
#             'message': ai_response
#         })

#     except Exception as e:
#         import traceback
#         error_details = traceback.format_exc()
#         print(f"Chat API Error: {str(e)}\n{error_details}")
#         return JsonResponse({
#             'error': str(e)
#         }, status=500)
