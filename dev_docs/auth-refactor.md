<!-- markdownlint-disable -->
# Auth refactor â€” email as primary identity

**Status**: In progress
**Date**: 2026-04-23

## Goal

Make **email** the unique login identifier for both doctors and patients. Phone becomes **optional** metadata. Remove the "phone-as-username" model used today for patients.

## Problem

Today:
- **Doctor** auth uses `email` as `User.username` (already correct).
- **Patient** auth uses `phone` as `User.username` â€” inconsistent, forces phone to be mandatory, and breaks if a patient doesn't have one.
- `Patient.phone` is `unique=True`; `Doctor.phone` is `unique=True`.
- `Patient.password` field on the model (plain text, legacy) â€” still present, should remain nullable and unused for auth.

## Target model

### Common
- `User.username` = email (lowercased, stripped).
- Django's built-in password hashing via `create_user` / `authenticate`.
- Login form: `email` + `password`.
- Registration: `email` + `password` + `confirm_password` + profile fields.

### Doctor
- Required: `name`, `email` (unique), `password`, `specialization`.
- Optional: `phone`, `hospital`.
- `Doctor.phone`: `CharField(max_length=15, blank=True, null=True)` â€” drop `unique=True`.

### Patient
- Required: `name`, `email` (unique), `password`, `date_of_birth`, `gender`.
- Optional: `phone`, `address`, `doctor`.
- `Patient.email`: **new** `EmailField(unique=True)`.
- `Patient.phone`: `CharField(max_length=15, blank=True, null=True)` â€” drop `unique=True`.
- Drop legacy `Patient.password` plaintext field (or keep for back-compat but stop writing). â†’ Decision: **drop** the legacy field in the same migration.

## Changes

### Models (`core/models.py`)
1. `Doctor.phone` â†’ `blank=True, null=True`, drop `unique=True`.
2. `Patient`: add `email = EmailField(unique=True)`.
3. `Patient.phone` â†’ `blank=True, null=True`, drop `unique=True`.
4. `Patient.password` â†’ remove.

### Migration
- Because we'll flush the DB afterwards (keeping superuser), a simple `makemigrations` + `migrate` is enough â€” no data migration needed.

### Forms / views (`core/template_views.py`)
- `DoctorRegistrationForm`: `phone` optional, `hospital` optional (already).
- `doctor_login`: unchanged semantics (already email-based).
- `PatientRegistrationForm`: replace `phone` requirement with `email` requirement; phone optional. Use email as username for `User.create_user`. Write `Patient.email`.
- `patient_login`: switch from phone lookup to email lookup; template updated to ask for email.
- `doctor_patient_add` (doctor adds a patient manually): require email, phone optional, generated password returned in UI.

### Templates
- `doctor/register.html`: mark phone as optional, keep email required.
- `patient/register.html`: remove the "phone is your login ID" copy; show email field as login ID; phone labelled optional.
- `patient/login.html`: email + password.
- `doctor/patient_add.html`: email required, phone optional.

### DB reset
- After migration & app changes are confirmed working:
  1. Back up superuser info (username, email, password hash).
  2. `manage.py flush --no-input` â€” clears *data* but keeps schema; preserves `auth_user` entries? No â€” `flush` wipes all tables. Instead use a small script: delete all non-superuser users + cascade, delete all Doctor/Patient/Visit/etc rows.
  3. Verify superuser still logs in at `/admin/`.

## Execution order

1. âœ… Write this doc.
2. Update `core/models.py`.
3. `makemigrations core` â†’ migration `0005_auth_email_refactor.py`.
4. Update forms, views, templates.
5. `migrate`.
6. Run `manage.py check` + smoke tests (`core.tests`).
7. Update existing 8 smoke tests if they reference phone-based patient login.
8. Data wipe script (preserve superuser).
9. Live HTTP smoke test of login/register pages.

## Non-goals

- We will NOT add email verification / password reset flows in this pass.
- We will NOT migrate existing patient data (DB is wiped anyway).
- DRF `/api/...` endpoints that mirror phone-based flows can follow in a later pass; priority here is the HTML portal.

## Acceptance

- New doctor can register & log in using email + password.
- New patient can register & log in using email + password, with no phone provided.
- Existing superuser still works at `/admin/`.
- `manage.py test core` passes.
