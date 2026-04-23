# AI / Developer context — Swajarnika

> Read this first when picking up the codebase. Pairs with [`design-doc-fixup.md`](design-doc-fixup.md) and [`tracker-fixup.md`](tracker-fixup.md).

## What this app is

A Django 5.2 healthcare portal with **two user personas** (doctor, patient) built on a custom `User` model with `is_doctor` / `is_patient` boolean flags. Patients can chat with an LLM that is given the patient's entire medical record as system context.

## Mental model

```
                 ┌──────────────┐
                 │  Django User │  (is_doctor / is_patient)
                 └──┬────────┬──┘
                    │ 1:1    │ 1:1
              ┌─────▼──┐  ┌──▼──────┐
              │ Doctor │  │ Patient │
              └───┬────┘  └─┬───────┘
                  │         │
                  │ 1:M     │ 1:M
                  ▼         ▼
              ┌──────────────┐
              │    Visit     │
              └──┬─────┬───┬─┘
         1:M    │     │   │  1:M
        ┌───────▼┐ ┌──▼───┐│  ┌───────────┐
        │  Test  │ │ Med. ││  │FileUpload │
        └────────┘ └──────┘│  └───────────┘
                           │
                           ▼
                       ┌────────┐
                       │AIPrompt│  (auto-generated summary)
                       └────────┘
      ┌──────────────────┐
      │  AIChatMessage   │ (chat history with the LLM, per patient)
      └──────────────────┘
```

## Two URL layers

The project has **two parallel URL configs** that overlap:

- `core/urls.py` — DRF JSON API (`/api/doctors/login/`, `/api/chat/`, …)
- `core/template_urls.py` — HTML page views (`/doctor/login/`, `/patient/dashboard/`, …) **and also re-declares** all the `/api/...` routes.

Root `healthcare_platform/urls.py` wires:

```
/admin/  → django admin
/api/    → core.urls           ← API
/        → core.template_urls  ← HTML (but also has its own api/ prefix → /api/api/ duplicates)
```

This double-registration is a known smell — see fix plan.

## Auth flow quirks

- Doctors log in with `email` as the username.
- Patients log in with `phone` as the username.
- `settings.LOGIN_URL = 'doctor_login'` — patient views use their own `@patient_required` decorator that redirects to `login` (wrong name — also buggy).
- The `Patient` model stores a **plaintext password** field in addition to the real hashed password on `User`. This is for "show this to the doctor after registration" UX, but it's a hard security no-go.

## AI / LLM integration

- Implemented in `core/utils.py` and `core/views.py::ChatAPIView`.
- Uses **Akash Network** chat completions API (OpenAI-compatible).
- Two different API keys appear hardcoded in source (`views.py` and `utils.py`) — pointing at two slightly different base URLs. One of them is probably dead.
- `get_patient_context(patient)` builds a huge multi-page system prompt from all visits, meds, tests, and **extracted PDF text** for every file the patient uploaded. Used every single chat turn — expensive.
- `get_ai_stream_response` exists but is unused; `ChatAPIView` does a single non-streaming POST.

## File structure map (quick reference)

| File | Role | Notable issues |
|------|------|----------------|
| `healthcare_platform/settings.py` | Django settings | Hardcoded `SECRET_KEY`, `DEBUG=True`, no env loading, `rest_framework` missing from `INSTALLED_APPS` |
| `settings.py` (repo root) | — | Stray 1-liner, delete |
| `.env` | — | Only has `DJANGO_SETTINGS_MODULE`, nothing loads it |
| `core/models.py` | ORM | `Patient.password` plaintext; models OK otherwise |
| `core/views.py` | DRF views | `Medication` not imported (crashes `create_ai_prompt`); hardcoded API key; ~150 lines of commented-out dead code |
| `core/template_views.py` | HTML views | Lots of `print()` debugging; doctor/patient password flows live here too |
| `core/serializers.py` | DRF serializers | `PatientRegisterSerializer` defined **twice** |
| `core/utils.py` | LLM + PDF helpers | Hardcoded API key; `is_akash_available()` called on every streaming request (double round-trip) |
| `core/urls.py` | API routes | Fine |
| `core/template_urls.py` | HTML routes | Re-declares all API routes under `/api/` too → double registration at `/api/api/...` via root include |
| `core/admin.py` | Admin | Minimal, OK |
| `core/templatetags/custom_filters.py` | `filename`, `markdown_format` | OK |
| `.blackboxrules` | — | Empty, can delete |

## Running locally

See [`../README.md`](../README.md). TL;DR:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Conventions going forward

- All new secrets go through `os.environ.get(...)` with a default from `.env`.
- Any new code passes `python manage.py check` with no warnings.
- Prefer editing existing files over creating new ones.
- Keep models backward-compatible with existing migrations unless the fix plan says otherwise.
- Document every non-trivial change in the active tracker.
