from django.urls import path

from .views import (
    AIInteractView,
    ChatAPIView,
    DoctorLoginView,
    DoctorRegisterView,
    FileUploadView,
    LogoutView,
    PatientLoginView,
    PatientProfileView,
    PatientRegisterView,
    VisitCreateView,
)

urlpatterns = [
    path('doctors/register/', DoctorRegisterView.as_view(), name='doctor-register'),
    path('doctors/login/', DoctorLoginView.as_view(), name='doctor-login'),
    path('patients/register/', PatientRegisterView.as_view(), name='patient-register'),
    path('patients/login/', PatientLoginView.as_view(), name='patient-login'),
    path('patients/profile/', PatientProfileView.as_view(), name='patient-profile'),
    path('visits/', VisitCreateView.as_view(), name='visit-create'),
    path('files/', FileUploadView.as_view(), name='file-upload'),
    path('ai/interact/', AIInteractView.as_view(), name='ai-interact'),
    path('logout/', LogoutView.as_view(), name='logout-api'),
    path('chat/', ChatAPIView.as_view(), name='chat-api'),
]
