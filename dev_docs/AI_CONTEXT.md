<!-- markdownlint-disable -->
# AI / Developer context â€” Swajarnika

> âš ï¸ **ARCHIVED â€” historical context only.** This file reflects the codebase *before*
> the April 2026 rehab. Newer behaviour (email-based auth, Groq LLM, revamped UI)
> is documented in [`auth-refactor.md`](auth-refactor.md) and [`demo-data.md`](demo-data.md).
> Do not treat the guidance below as current; keep it for background only.

> Read this first when picking up the codebase. Pairs with [`design-doc-fixup.md`](design-doc-fixup.md) and [`tracker-fixup.md`](tracker-fixup.md).

## What this app is

A Django 5.2 healthcare portal with **two user personas** (doctor, patient) built on a custom `User` model with `is_doctor` / `is_patient` boolean flags. Patients can chat with an LLM that is given the patient's entire medical record as system context.

## Mental model

```
                 â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                 â”‚  Django User â”‚  (is_doctor / is_patient)
                 â””â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”˜
                    â”‚ 1:1    â”‚ 1:1
              â”Œâ”€â”€â”€â”€â”€â–¼â”€â”€â”  â”Œâ”€â”€â–¼â”€â”€â”€â”€â”€â”€â”
              â”‚ Doctor â”‚  â”‚ Patient â”‚
              â””â”€â”€â”€â”¬â”€â”€â”€â”€â”˜  â””â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
                  â”‚         â”‚
                  â”‚ 1:M     â”‚ 1:M
                  â–¼         â–¼
              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
              â”‚    Visit     â”‚
              â””â”€â”€â”¬â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”¬â”€â”˜
         1:M    â”‚     â”‚   â”‚  1:M
        â”Œâ”€â”€â”€â”€â”€â”€â”€â–¼â” â”Œâ”€â”€â–¼â”€â”€â”€â”â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
        â”‚  Test  â”‚ â”‚ Med. â”‚â”‚  â”‚FileUpload â”‚
        â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”˜â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                           â”‚
                           â–¼
                       â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”
                       â”‚AIPromptâ”‚  (auto-generated summary)
                       â””â”€â”€â”€â”€â”€â”€â”€â”€â”˜
      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
      â”‚  AIChatMessage   â”‚ (chat history with the LLM, per patient)
      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Two URL layers

The project has **two parallel URL configs** that overlap:

- `core/urls.py` â€” DRF JSON API (`/api/doctors/login/`, `/api/chat/`, â€¦)
- `core/template_urls.py` â€” HTML page views (`/doctor/login/`, `/patient/dashboard/`, â€¦) **and also re-declares** all the `/api/...` routes.

Root `healthcare_platform/urls.py` wires:

```
/admin/  â†’ django admin
/api/    â†’ core.urls           â† API
/        â†’ core.template_urls  â† HTML (but also has its own api/ prefix â†’ /api/api/ duplicates)
```

This double-registration is a known smell â€” see fix plan.

## Auth flow quirks

- Doctors log in with `email` as the username.
- Patients log in with `phone` as the username.
- `settings.LOGIN_URL = 'doctor_login'` â€” patient views use their own `@patient_required` decorator that redirects to `login` (wrong name â€” also buggy).
- The `Patient` model stores a **plaintext password** field in addition to the real hashed password on `User`. This is for "show this to the doctor after registration" UX, but it's a hard security no-go.

## AI / LLM integration

- Implemented in `core/utils.py` and `core/views.py::ChatAPIView`.
- Uses **Akash Network** chat completions API (OpenAI-compatible).
- Two different API keys appear hardcoded in source (`views.py` and `utils.py`) â€” pointing at two slightly different base URLs. One of them is probably dead.
- `get_patient_context(patient)` builds a huge multi-page system prompt from all visits, meds, tests, and **extracted PDF text** for every file the patient uploaded. Used every single chat turn â€” expensive.
- `get_ai_stream_response` exists but is unused; `ChatAPIView` does a single non-streaming POST.

## File structure map (quick reference)

| File | Role | Notable issues |
|------|------|----------------|
| `healthcare_platform/settings.py` | Django settings | Hardcoded `SECRET_KEY`, `DEBUG=True`, no env loading, `rest_framework` missing from `INSTALLED_APPS` |
| `settings.py` (repo root) | â€” | Stray 1-liner, delete |
| `.env` | â€” | Only has `DJANGO_SETTINGS_MODULE`, nothing loads it |
| `core/models.py` | ORM | `Patient.password` plaintext; models OK otherwise |
| `core/views.py` | DRF views | `Medication` not imported (crashes `create_ai_prompt`); hardcoded API key; ~150 lines of commented-out dead code |
| `core/template_views.py` | HTML views | Lots of `print()` debugging; doctor/patient password flows live here too |
| `core/serializers.py` | DRF serializers | `PatientRegisterSerializer` defined **twice** |
| `core/utils.py` | LLM + PDF helpers | Hardcoded API key; `is_akash_available()` called on every streaming request (double round-trip) |
| `core/urls.py` | API routes | Fine |
| `core/template_urls.py` | HTML routes | Re-declares all API routes under `/api/` too â†’ double registration at `/api/api/...` via root include |
| `core/admin.py` | Admin | Minimal, OK |
| `core/templatetags/custom_filters.py` | `filename`, `markdown_format` | OK |
| `.blackboxrules` | â€” | Empty, can delete |

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
