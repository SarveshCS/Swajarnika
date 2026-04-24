<!-- markdownlint-disable -->
# Design doc â€” Codebase fix-up plan

> âš ï¸ **ARCHIVED â€” historical plan, completed.** The phases below were all executed on 2026-04-23.
> See [`tracker-fixup.md`](tracker-fixup.md) for the closed-out tracker, and
> [`auth-refactor.md`](auth-refactor.md) / [`demo-data.md`](demo-data.md) for current work.

**Status:** Draft Â· **Owner:** Team Â· **Created:** 2026-04-23

This doc describes how we will bring the Swajarnika codebase back to a clean, consistent, working state after ~1 year of inactivity. It is the source of truth for *what* we are changing and *why*. The step-by-step execution log lives in [`tracker-fixup.md`](tracker-fixup.md).

---

## 1. Goals

1. App runs cleanly from a fresh clone with one `pip install` + `migrate` + `runserver`.
2. No secrets in source. All configurable values come from `.env`.
3. No dead/commented-out code in the main modules.
4. No crashing code paths (missing imports, duplicate classes, wrong URLs).
5. Consistent code style (formatted with `black`, imports cleaned).
6. A working admin + starter superuser + empty DB as a clean baseline.
7. A minimal but honest `.gitignore` and a working `requirements.txt`.

**Non-goals (for this pass):**

- Rewriting the UI.
- Moving off SQLite.
- Replacing the LLM backend.
- Adding tests beyond a smoke-test level.

## 2. Guiding principles

- **Small, reversible, verifiable steps.** After each step the app must still boot.
- **Don't break migrations.** Schema stays compatible unless explicitly flagged.
- **Docs follow code.** Update `AI_CONTEXT.md` + tracker as we go.
- **Respect the existing tech stack.** Django + DRF + SQLite + Akash LLM stays.

## 3. Identified issues

Grouped by severity.

### 3.1 Blockers (app is broken or insecure as-is)

| # | Issue | Location | Why it matters |
|---|-------|----------|----------------|
| B1 | `djangorestframework` used but **not in `requirements.txt`** and **not in `INSTALLED_APPS`** | `requirements.txt`, `healthcare_platform/settings.py` | DRF views (including `/api/chat/`) 500 on a fresh install. |
| B2 | `Medication` not imported in `core/views.py::create_ai_prompt` | `core/views.py` | `NameError` whenever a doctor creates a visit via API. |
| B3 | Hardcoded Django `SECRET_KEY` | `healthcare_platform/settings.py` | Committed secret; must be env-driven. |
| B4 | Hardcoded LLM API keys (two of them) | `core/views.py`, `core/utils.py` | Committed secret; must be env-driven. |
| B5 | `Patient.password` stored in plaintext | `core/models.py`, `core/template_views.py` | Security red flag. Real password is already on `User`; this field should store only a display-once token or be removed. |
| B6 | Duplicate `PatientRegisterSerializer` class | `core/serializers.py` | Second definition silently wins; `password` field behavior is confusing. |

### 3.2 Major (wrong but not yet crashing)

| # | Issue | Location |
|---|-------|----------|
| M1 | Stray `settings.py` at repo root | `./settings.py` |
| M2 | `.env` only contains `DJANGO_SETTINGS_MODULE`, no loader | `.env`, `healthcare_platform/settings.py` |
| M3 | Double-registered URL routes (`/api/api/...` via include chain) | `core/template_urls.py` + `healthcare_platform/urls.py` |
| M4 | `LOGIN_URL = 'doctor_login'` is wrong for patient-only views; `@patient_required` redirects to a non-existent `login` name | `settings.py`, `core/template_views.py` |
| M5 | `DEBUG = True` and `ALLOWED_HOSTS = []` hardcoded | `healthcare_platform/settings.py` |
| M6 | `print()` statements used as logging in `patient_login` | `core/template_views.py` |

### 3.3 Minor (cleanup)

| # | Issue | Location |
|---|-------|----------|
| N1 | ~150 lines of commented-out dead code | `core/views.py` |
| N2 | Empty `.blackboxrules` | `./.blackboxrules` |
| N3 | No `.gitignore` | repo root |
| N4 | Inconsistent formatting (mix of Django and PEP8 drift) | whole `core/` |
| N5 | No README (fixed) | repo root |
| N6 | `AIPrompt.prompt` vs `prompt_text` attribute mismatch guessed in `utils.py` | `core/utils.py` |
| N7 | `get_ai_stream_response` exists, is exported, and is never used | `core/utils.py` |

## 4. Target end-state

After the fix-up:

```
Swajarnika/
â”œâ”€â”€ README.md                       âœ… done
â”œâ”€â”€ .gitignore                       new
â”œâ”€â”€ .env.example                     new â€” documents required vars
â”œâ”€â”€ .env                             local-only, real secrets
â”œâ”€â”€ requirements.txt                 includes djangorestframework, python-dotenv
â”œâ”€â”€ manage.py
â”œâ”€â”€ db.sqlite3                       fresh / empty
â”œâ”€â”€ healthcare_platform/
â”‚   â”œâ”€â”€ settings.py                  reads from env, no hardcoded secrets
â”‚   â””â”€â”€ urls.py                      unchanged
â”œâ”€â”€ core/
â”‚   â”œâ”€â”€ views.py                     no commented dead code, imports fixed, keys from env
â”‚   â”œâ”€â”€ template_views.py            no prints, login url names fixed
â”‚   â”œâ”€â”€ serializers.py               single PatientRegisterSerializer
â”‚   â”œâ”€â”€ utils.py                     key from env
â”‚   â”œâ”€â”€ urls.py                      unchanged
â”‚   â””â”€â”€ template_urls.py             no /api/ re-registration
â””â”€â”€ dev_docs/
    â”œâ”€â”€ AI_CONTEXT.md                âœ… done
    â”œâ”€â”€ design-doc-fixup.md          âœ… this file
    â””â”€â”€ _tracker_active.md           running log
```

## 5. Plan â€” phased

Each phase ends with a working `python manage.py runserver`.

### Phase 0 â€” baseline reset  *(executed now on user request)*

1. Create `README.md` âœ…
2. Create `dev_docs/` with `AI_CONTEXT.md`, `design-doc-fixup.md`, `_tracker_active.md` âœ…
3. **Wipe the database** (`manage.py flush`) to remove all previous users, superusers, and records.
4. User creates a fresh superuser.

### Phase 1 â€” make it boot correctly

1. Fix `requirements.txt`: add `djangorestframework`, `python-dotenv`.
2. Add `rest_framework` to `INSTALLED_APPS`.
3. Fix `Medication` import in `core/views.py`.
4. Remove duplicate `PatientRegisterSerializer`.
5. Delete stray root-level `settings.py`.
6. Verify: `python manage.py check` clean, `runserver` clean.

### Phase 2 â€” secrets & config hygiene

1. Add `python-dotenv` loader at top of `healthcare_platform/settings.py`.
2. Move `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` to env.
3. Move Akash API key + base URL + model name to env.
4. Commit a `.env.example` with placeholder values.
5. Add `.gitignore` (`.env`, `db.sqlite3`, `__pycache__/`, `staticfiles/`, `media/`, `.venv/`).

### Phase 3 â€” URL & auth consistency

1. Remove duplicate `/api/...` routes from `core/template_urls.py`.
2. Fix `LOGIN_URL` / `patient_required` redirect targets to correct URL names.
3. Replace `print()` debug in `patient_login` with `logging`.

### Phase 4 â€” dead code purge + formatting

1. Delete commented-out blocks in `core/views.py`.
2. Drop empty `.blackboxrules`.
3. Run `black core/ healthcare_platform/`.
4. Run `isort` (or equivalent manual tidy).

### Phase 5 â€” model & serializer polish

1. Decide: remove `Patient.password` or rename it to `initial_password` and flag it for "display once / clear on first login". Migration path documented.
2. Make `get_ai_stream_response` either wired up or deleted.
3. Align `AIPrompt` attribute access in `utils.py` with the actual model field (`prompt`, not `prompt_text`).

### Phase 6 â€” smoke tests

1. Add a minimal `core/tests.py` that:
   - Creates a doctor + patient.
   - Asserts doctor can list their patients.
   - Asserts patient can reach `/patient/dashboard/` after login.
2. `python manage.py test` must pass.

## 6. Acceptance criteria

- `git clone` â†’ `pip install -r requirements.txt` â†’ `migrate` â†’ `runserver` works with no edits.
- `python manage.py check --deploy` only warns about dev-only items (DEBUG, SECRET_KEY length).
- No secret strings remain in tracked files (grep for `sk-`, `django-insecure-`).
- `python manage.py test` passes.
- `README.md` accurately describes how to run.

## 7. Out of scope / future work

- Switching to Postgres.
- Streaming chat UI.
- Proper role-based permissions via DRF permission classes (currently inline).
- Celery for async PDF extraction on upload instead of on every chat turn.
- Dockerfile + docker-compose.
