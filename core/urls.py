from django.urls import path
from .views import (
    DoctorRegisterView, DoctorLoginView, PatientRegisterView,
    VisitCreateView, FileUploadView, AIInteractView, 
    PatientLoginView, PatientProfileView, LogoutView
    # Add other view imports here as needed.
)
from . import template_views

urlpatterns = [
    path('doctors/register/', DoctorRegisterView.as_view(), name='doctor-register'),
    path('doctors/login/', DoctorLoginView.as_view(), name='doctor-login'),
    path('patients/register/', PatientRegisterView.as_view(), name='patient-register'),
    path('patients/login/', PatientLoginView.as_view(), name='patient-login'),
    path('patients/profile/', PatientProfileView.as_view(), name='patient-profile'),
    path('visits/', VisitCreateView.as_view(), name='visit-create'),
    path('files/', FileUploadView.as_view(), name='file-upload'),
    path('ai/interact/', AIInteractView.as_view(), name='ai-interact'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('patient/ai-chat/', template_views.patient_ai_chat, name='patient_ai_chat'),
    # Add endpoints for patient login, view medications, tests, and files as required.
]
