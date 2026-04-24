<!-- markdownlint-disable -->
# Swajarnika

A Django-based healthcare platform that connects **doctors** and **patients**, with an AI-powered chat assistant for patients (backed by the Groq LLM API).

> Status: College project being rehabilitated after ~1 year of inactivity. See [`dev_docs/design-doc-fixup.md`](dev_docs/design-doc-fixup.md) for the active refactor plan.

---

## Features

- **Doctor portal** â€” register, log in, manage patients, create visits, prescribe medications, order tests, upload files.
- **Patient portal** â€” log in, view visits / medications / tests / files, chat with an AI assistant that has full medical-record context.
- **AI chat** â€” streams responses from an LLM, grounded in the patient's records and uploaded PDFs.
- **Admin** â€” Django admin at `/admin/` for full data management.

## Tech stack

- Python 3.10+
- Django 5.2
- Django REST Framework (templates + DRF API)
- SQLite (default, dev only)
- Groq chat completions API (LLM, OpenAI-compatible)
- `PyPDF2` for PDF text extraction, `markdown` for rendering AI replies

## Project layout

```
Swajarnika/
â”œâ”€â”€ manage.py
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ .env                        # local env vars (not committed)
â”œâ”€â”€ db.sqlite3                  # dev database
â”œâ”€â”€ healthcare_platform/        # Django project (settings, root urls, wsgi/asgi)
â”œâ”€â”€ core/                       # main app
â”‚   â”œâ”€â”€ models.py               # User, Doctor, Patient, Visit, Test, Medication, FileUpload, AIPrompt, AIChatMessage
â”‚   â”œâ”€â”€ views.py                # DRF API views
â”‚   â”œâ”€â”€ template_views.py       # HTML page views
â”‚   â”œâ”€â”€ urls.py                 # DRF API routes
â”‚   â”œâ”€â”€ template_urls.py        # HTML routes (and re-declares API routes â€” to be fixed)
â”‚   â”œâ”€â”€ serializers.py
â”‚   â”œâ”€â”€ utils.py                # Groq API client, patient context builder, PDF extraction
â”‚   â”œâ”€â”€ admin.py
â”‚   â”œâ”€â”€ templates/core/         # HTML templates (doctor/, patient/)
â”‚   â”œâ”€â”€ static/core/
â”‚   â”œâ”€â”€ templatetags/
â”‚   â””â”€â”€ migrations/
â”œâ”€â”€ media/uploads/              # patient file uploads
â””â”€â”€ dev_docs/                   # internal developer documentation
```

## Quick start (Windows / PowerShell)

```powershell
# 1. Clone and enter the repo
cd full_website\Swajarnika

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply migrations
python manage.py migrate

# 5. Create an admin account
python manage.py createsuperuser

# 6. Run the dev server
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.
Admin site: http://127.0.0.1:8000/admin/

## Environment variables

Create a `.env` file in the project root (already present). The fix plan will move secrets here; currently the file is mostly unused.

```env
# Django
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

# Groq LLM API
GROQ_API_KEY=gsk-xxxxxxxx
GROQ_API_BASE=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
```

## Key URLs

| Path | Description |
|------|-------------|
| `/` | Landing page |
| `/doctor/login/`, `/doctor/register/`, `/doctor/dashboard/` | Doctor UI |
| `/patient/login/`, `/patient/register/`, `/patient/dashboard/` | Patient UI |
| `/patient/ai-chat/` | AI chat page |
| `/api/...` | DRF JSON endpoints |
| `/admin/` | Django admin |

## Known issues (being fixed)

See [`dev_docs/design-doc-fixup.md`](dev_docs/design-doc-fixup.md) for the full list and plan. Highlights:

- `djangorestframework` is used but missing from `requirements.txt` / `INSTALLED_APPS`.
- API keys and Django `SECRET_KEY` are hardcoded in source.
- `Medication` not imported in `core/views.py::create_ai_prompt` (runtime crash).
- Patient password stored in plaintext on the `Patient` model.
- Duplicate `PatientRegisterSerializer` class.
- Large blocks of commented-out dead code.
- Stray `settings.py` at repo root.
- No `.gitignore`, no tests.

## License

College project â€” no license granted.
