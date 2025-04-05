from django.urls import path
from . import template_views

urlpatterns = [
    # Doctor URLs
    path('doctor/register/', template_views.doctor_register, name='doctor_register'),
    path('doctor/login/', template_views.doctor_login, name='doctor_login'),
    path('doctor/dashboard/', template_views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/patient/add/', template_views.doctor_patient_add, name='doctor_patient_add'),
    path('doctor/patient/<int:patient_id>/', template_views.doctor_patient_detail, name='doctor_patient_detail'),
    path('doctor/patient/<int:patient_id>/update/', template_views.doctor_patient_update, name='doctor_patient_update'),
    path('doctor/patient/<int:patient_id>/delete/', template_views.doctor_patient_delete, name='doctor_patient_delete'),
    
    # Add these new URL patterns
    path('doctor/patient/<int:patient_id>/visit/add/', template_views.doctor_visit_add, name='doctor_visit_add'),
    path('doctor/visit/<int:visit_id>/', template_views.doctor_visit_detail, name='doctor_visit_detail'),
    path('doctor/visit/<int:visit_id>/delete/', template_views.doctor_visit_delete, name='doctor_visit_delete'),
    path('doctor/patient/<int:patient_id>/file/upload/', template_views.doctor_file_upload, name='doctor_file_upload'),
    path('doctor/file/<int:file_id>/delete/', template_views.doctor_file_delete, name='doctor_file_delete'),
    
    # Patient URLs
    path('patient/login/', template_views.patient_login, name='patient_login'),
    path('patient/dashboard/', template_views.patient_dashboard, name='patient_dashboard'),
    path('patient/visit/<int:visit_id>/', template_views.patient_visit_detail, name='patient_visit_detail'),
    path('patient/medications/', template_views.patient_medications, name='patient_medications'),
    path('patient/tests/', template_views.patient_tests, name='patient_tests'),
    path('patient/files/', template_views.patient_files, name='patient_files'),
    path('patient/ai-chat/', template_views.patient_ai_chat, name='patient_ai_chat'),
    
    # Common URLs
    path('logout/', template_views.logout_view, name='logout'),
]