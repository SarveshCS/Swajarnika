"""Smoke tests for Swajarnika.

These are intentionally minimal — they confirm that the core pages render,
the auth flows resolve to the right URLs, and the two-role custom user model
works. They are not a replacement for proper unit tests.
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Doctor, Patient

User = get_user_model()


class PublicPageTests(TestCase):
    def test_index_loads(self):
        resp = self.client.get(reverse('index'))
        self.assertEqual(resp.status_code, 200)

    def test_doctor_login_page_loads(self):
        resp = self.client.get(reverse('doctor_login'))
        self.assertEqual(resp.status_code, 200)

    def test_patient_login_page_loads(self):
        resp = self.client.get(reverse('patient_login'))
        self.assertEqual(resp.status_code, 200)


class DoctorPatientFlowTests(TestCase):
    def setUp(self):
        self.doctor_user = User.objects.create_user(
            username='doc@example.com',
            email='doc@example.com',
            password='testpass123',
            is_doctor=True,
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            name='Dr. Test',
            email='doc@example.com',
            specialization='GP',
            phone='1000000001',
        )

        self.patient_user = User.objects.create_user(
            username='9999999999',
            password='patientpw123',
            is_patient=True,
        )
        self.patient = Patient.objects.create(
            user=self.patient_user,
            doctor=self.doctor,
            name='Pat Test',
            date_of_birth=date(2000, 1, 1),
            gender='M',
            phone='9999999999',
        )

    def test_doctor_can_reach_dashboard(self):
        self.client.login(username='doc@example.com', password='testpass123')
        resp = self.client.get(reverse('doctor_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Pat Test')

    def test_patient_can_reach_dashboard(self):
        self.client.login(username='9999999999', password='patientpw123')
        resp = self.client.get(reverse('patient_dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_patient_required_redirects_anonymous(self):
        resp = self.client.get(reverse('patient_dashboard'))
        # Decorator redirects to patient_login
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('patient_login'), resp.url)


class ModelTests(TestCase):
    def test_user_str_for_doctor(self):
        u = User.objects.create_user(
            username='d2@example.com', password='x', is_doctor=True
        )
        self.assertIn('Doctor', str(u))

    def test_user_str_for_patient(self):
        u = User.objects.create_user(
            username='1234567890', password='x', is_patient=True
        )
        self.assertIn('Patient', str(u))
