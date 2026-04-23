# Fix-up tracker — COMPLETE ✅

> Pairs with [`design-doc-fixup.md`](design-doc-fixup.md). All phases completed on 2026-04-23.

**Legend:** `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` skipped (documented)

---

## Phase 0 — baseline reset

- [x] Create `README.md`
- [x] Create `dev_docs/AI_CONTEXT.md`
- [x] Create `dev_docs/design-doc-fixup.md`
- [x] Create `dev_docs/_tracker_active.md` (this file)
- [x] Wipe database (`python manage.py flush --no-input`)
- [x] User creates a fresh superuser
- [-] Delete `media/uploads/*` — not needed (user retained files)

## Phase 1 — make it boot correctly

- [x] Add `djangorestframework` to `requirements.txt`
- [x] Add `python-dotenv` to `requirements.txt`
- [x] Add `'rest_framework'` to `INSTALLED_APPS`
- [x] Fix `from .models import ... Medication` in `core/views.py`
- [x] Remove duplicate `PatientRegisterSerializer` class from `core/serializers.py`
- [x] Delete stray `./settings.py` (repo root)
- [x] Verify: `python manage.py check` clean
- [x] Verify: `python manage.py runserver` boots with no ImportError

## Phase 2 — secrets & config hygiene

- [x] Add `dotenv.load_dotenv()` at top of `healthcare_platform/settings.py`
- [x] `SECRET_KEY` ← env (with safe default for dev)
- [x] `DEBUG` ← env
- [x] `ALLOWED_HOSTS` ← env
- [x] `AKASH_API_KEY`, `AKASH_API_BASE`, `AKASH_MODEL` ← env (consumed in `core/utils.py` and `core/views.py`)
- [x] Create `.env.example`
- [x] Create `.gitignore`
- [x] Regenerate `.env` with a fresh `SECRET_KEY`

## Phase 3 — URL & auth consistency

- [x] Remove duplicated `path('api/...')` entries from `core/template_urls.py`
- [x] Fix `patient_required` redirect target (`'login'` → `'patient_login'`)
- [x] Remove `patient_ai_chat` name collision between API and template URL configs (API renamed to `chat-api` only)
- [x] Replace `print()` debug in `patient_login` with `logging`
- [-] Split `LOGIN_URL` per role — kept as-is; acceptable default for mixed-role admin flows

## Phase 4 — dead code purge + formatting

- [x] Delete commented-out legacy `ChatAPIView` and `chat_api` blocks in `core/views.py`
- [x] Delete empty `.blackboxrules`
- [x] Clean up unused imports in `core/views.py` and `core/urls.py`
- [-] Run full `black` / `isort` pass — manually tidied imports in modified files only; a full repo-wide reformat would noise-up unchanged files

## Phase 5 — model & serializer polish

- [x] Align `AIPrompt.prompt` attribute access in `core/utils.py`
- [-] Remove/rename `Patient.password` — left as-is, noted as a future security item. Removing would require a migration and UI change to the "show credentials to doctor" flow.
- [-] Wire up or delete `get_ai_stream_response` — left as-is (unused but not harmful; streaming UI is future work)

## Phase 6 — smoke tests

- [x] Add `core/tests.py` with 8 smoke tests
- [x] `python manage.py test core` → `Ran 8 tests. OK`

## Final verification

- [x] `python manage.py check` → clean
- [x] `python manage.py test core` → 8/8 pass
- [x] `python manage.py runserver` → boots; `/` and `/doctor/login/` return HTTP 200
- [x] No hardcoded secrets in tracked source (`grep sk-` and `django-insecure-` both empty apart from `.env.example` placeholders)

---

## Session log

- **2026-04-23** — Phase 0 done: README + dev_docs scaffolding + DB flush.
- **2026-04-23** — User created fresh superuser.
- **2026-04-23** — Phases 1–6 executed in a single session. 8 smoke tests green. Server boots and responds 200. Tracker renamed off `_active`.

## Known future work (out of scope for this pass)

- Remove `Patient.password` plaintext field via migration.
- Wire up streaming chat, delete `get_ai_stream_response` if not used.
- Proper DRF permission classes instead of inline `hasattr(user, 'doctor')` checks.
- Move from SQLite to Postgres for anything beyond local dev.
- Dockerfile + `docker-compose.yml`.
- Cache extracted PDF text on upload instead of on every chat turn.
