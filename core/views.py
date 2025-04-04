from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login
from .serializers import DoctorRegisterSerializer

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

from django.contrib.auth import get_user_model
from .models import Patient
from .serializers import PatientRegisterSerializer

User = get_user_model()

import random, string

def make_random_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

from rest_framework.permissions import IsAuthenticated

class PatientRegisterView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def post(self, request):
        # Ensure the user is a doctor
        if not hasattr(request.user, 'doctor'):
            return Response({'error': 'Only doctors can register patients.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        # Generate a secure random password for the patient
        password = make_random_password()
        data['password'] = password  # You may pass this to the patient in response
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
            patient = serializer.save(user=user, doctor=request.user.doctor, password=password)
            return Response({'patient_id': patient.id, 'generated_password': password}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .models import Visit, Medication, AIPrompt
from .serializers import VisitSerializer

def create_ai_prompt(visit):
    # Gather diagnosis and medications details
    medications = Medication.objects.filter(visit=visit)
    prompt_text = f"Diagnosis: {visit.diagnosis}\nTreatment: {visit.treatment_plan}\n"
    for med in medications:
        prompt_text += f"Medication: {med.medication_name} - {med.instructions} (Missed dose: {med.missed_dose_instructions})\n"
    AIPrompt.objects.create(patient=visit.patient, visit=visit, prompt=prompt_text)

class VisitCreateView(APIView):
    def post(self, request):
        serializer = VisitSerializer(data=request.data)
        if serializer.is_valid():
            visit = serializer.save()
            create_ai_prompt(visit)  # update AI prompt table
            return Response({'visit_id': visit.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .models import FileUpload
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import FileUploadSerializer  # create a serializer for this model similarly

class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'File uploaded successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .models import AIPrompt

class AIInteractView(APIView):
    def post(self, request):
        patient_id = request.data.get('patient_id')
        question = request.data.get('question')
        # Get the latest AI prompt for the patient
        try:
            ai_prompt = AIPrompt.objects.filter(patient_id=patient_id).latest('created_at')
            # Here you would normally call your AI assistant. For PoC, return a dummy answer.
            answer = f"Based on your recent visit prompt: {ai_prompt.prompt}\nYour question: {question}"
            return Response({'answer': answer})
        except AIPrompt.DoesNotExist:
            return Response({'error': 'No AI prompt found for this patient'}, status=status.HTTP_404_NOT_FOUND)
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
from .serializers import PatientRegisterSerializer

class PatientProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            patient = request.user.patient
            serializer = PatientRegisterSerializer(patient)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except:
            return Response({'error': 'Not a patient'}, status=status.HTTP_403_FORBIDDEN)
        
from django.contrib.auth import logout
class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)