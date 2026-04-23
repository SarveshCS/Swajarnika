# Demo data — sample doctors, patients, visits

**Status**: Active reference. Use this when preparing a demo or presentation.
**Last updated**: 2026-04-23

> All names, phone numbers and medical details below are fictional. Use them as
> a ready-to-copy script for live demos so the portal shows realistic, coherent
> patient stories instead of "Test Patient / asdf asdf".

---

## How to use this file

1. Make sure the DB is empty-ish — only the superuser should remain
   (see `auth-refactor.md` for the cleanup script).
2. Register the three doctors below via `/doctor/register/`.
3. Log in as each doctor and either register-via-portal or use **Add Patient**
   to create the patients listed under each doctor.
4. For each patient, create the visits under **New Visit**, using the diagnosis,
   medications, tests and notes exactly as scripted. This gives the AI chat
   assistant enough grounded context to answer meaningfully during the demo.

Passwords below are obviously not production-grade; they are intentionally
memorable so you can type them quickly on stage.

---

## Doctors

### Dr. Meera Nair — General Medicine

| Field | Value |
| --- | --- |
| Email | `meera.nair@swajarnika.dev` |
| Password | `Demo#1234` |
| Specialization | General Medicine |
| Phone | `+91 98450 11111` |
| Hospital | *Swajarnika Polyclinic, Bengaluru* |

### Dr. Arjun Menon — Cardiology

| Field | Value |
| --- | --- |
| Email | `arjun.menon@swajarnika.dev` |
| Password | `Demo#1234` |
| Specialization | Cardiology |
| Phone | `+91 98450 22222` |
| Hospital | *Manipal Heart Centre, Bengaluru* |

### Dr. Priya Iyer — Pediatrics

| Field | Value |
| --- | --- |
| Email | `priya.iyer@swajarnika.dev` |
| Password | `Demo#1234` |
| Specialization | Pediatrics |
| Phone | `+91 98450 33333` |
| Hospital | *Rainbow Children's Hospital, Bengaluru* |

---

## Patients

### 1. Rahul Deshpande — under Dr. Meera Nair

| Field | Value |
| --- | --- |
| Email | `rahul.deshpande@example.com` |
| Password | `Patient#1` |
| DOB | 1988-06-12 |
| Gender | M |
| Phone | `+91 99000 10001` |
| Address | *2B, HSR Layout, Bengaluru* |
| Primary doctor | Dr. Meera Nair |

#### Visit 1 — 2026-03-18 (Type 2 Diabetes follow-up)

- **Diagnosis**: Type 2 Diabetes Mellitus, poorly controlled. HbA1c 8.6%.
- **Treatment plan**: Titrate oral hypoglycemics; dietary counselling; 30 min brisk walk 5×/week; repeat HbA1c in 12 weeks.
- **Notes**: Reports increased thirst and nocturia. BMI 28.4.

**Medications**

| Name | Reason | Instructions | If missed |
| --- | --- | --- | --- |
| Metformin 1000 mg | Primary glucose control | 1 tab after breakfast and after dinner | Take with the next meal; do NOT double dose |
| Glimepiride 2 mg | Add-on sulfonylurea | 1 tab 30 min before breakfast | Skip if within 6 hours of next meal |
| Atorvastatin 10 mg | Dyslipidemia | 1 tab at bedtime | Take next evening; do not double up |

**Tests**

| Test | Region | Reason |
| --- | --- | --- |
| HbA1c | Blood | Recheck glycemic control in 12 weeks |
| Fasting lipid profile | Blood | Baseline for statin therapy |
| Serum creatinine + eGFR | Blood | Monitor renal function on metformin |

---

### 2. Anjali Krishnan — under Dr. Meera Nair

| Field | Value |
| --- | --- |
| Email | `anjali.krishnan@example.com` |
| Password | `Patient#1` |
| DOB | 1995-09-23 |
| Gender | F |
| Phone | `+91 99000 10002` |
| Primary doctor | Dr. Meera Nair |

#### Visit 1 — 2026-04-02 (Acute pharyngitis)

- **Diagnosis**: Acute bacterial pharyngitis. Centor score 3/4.
- **Treatment plan**: 5-day antibiotic course, symptomatic relief, rest and fluids.
- **Notes**: Throat swab sent; no known penicillin allergy.

**Medications**

| Name | Reason | Instructions | If missed |
| --- | --- | --- | --- |
| Amoxicillin 500 mg | Bacterial pharyngitis | 1 cap every 8 hours for 5 days | Take as soon as remembered, then continue schedule |
| Paracetamol 500 mg | Fever / throat pain | 1 tab every 6 hours as needed (max 4/day) | Skip and continue next dose only if needed |

**Tests**

| Test | Region | Reason |
| --- | --- | --- |
| Throat swab culture | Oropharynx | Confirm bacterial etiology |
| CBC | Blood | Baseline WBC |

---

### 3. Sundar Rao — under Dr. Arjun Menon

| Field | Value |
| --- | --- |
| Email | `sundar.rao@example.com` |
| Password | `Patient#1` |
| DOB | 1964-02-04 |
| Gender | M |
| Phone | `+91 99000 20001` |
| Address | *14, Jayanagar 4th Block, Bengaluru* |
| Primary doctor | Dr. Arjun Menon |

#### Visit 1 — 2026-02-20 (Post-MI review)

- **Diagnosis**: Post-MI (anterior wall, 8 weeks ago). LVEF 38%.
- **Treatment plan**: Continue GDMT, cardiac rehab 2×/week, low-salt DASH diet.
- **Notes**: No chest pain. NYHA II. BP 128/82, HR 68.

**Medications**

| Name | Reason | Instructions | If missed |
| --- | --- | --- | --- |
| Aspirin 75 mg | Secondary prevention | 1 tab after lunch | Take when remembered same day; do NOT double dose |
| Clopidogrel 75 mg | Dual antiplatelet (DAPT, 12 months) | 1 tab after breakfast | Take ASAP; do NOT double dose |
| Atorvastatin 40 mg | High-intensity statin | 1 tab at bedtime | Take next evening |
| Metoprolol succ. 50 mg | Beta-blockade post-MI | 1 tab in the morning | Take if within 12 hours; else skip |
| Ramipril 5 mg | ACE inhibition, LV remodelling | 1 tab in the morning | Take when remembered; do NOT double dose |

**Tests**

| Test | Region | Reason |
| --- | --- | --- |
| 2D Echocardiogram | Heart | Reassess LVEF at 3 months |
| Lipid profile | Blood | Confirm LDL < 55 mg/dL on high-intensity statin |
| LFT + CK | Blood | Statin safety monitoring |

#### Visit 2 — 2026-04-10 (Follow-up, mild ankle edema)

- **Diagnosis**: Post-MI; mild ankle edema, likely volume-related.
- **Treatment plan**: Add low-dose diuretic, recheck weight daily, repeat echo in 2 months.
- **Notes**: BP 120/78, HR 64. Weight up 2 kg in 3 weeks.

**Medications** (additions)

| Name | Reason | Instructions | If missed |
| --- | --- | --- | --- |
| Furosemide 20 mg | Mild volume overload | 1 tab in the morning | Skip and take next scheduled dose; do NOT take at night |

---

### 4. Kavya Sharma — under Dr. Priya Iyer

| Field | Value |
| --- | --- |
| Email | `kavya.sharma@example.com` (guardian) |
| Password | `Patient#1` |
| DOB | 2019-11-05 |
| Gender | F |
| Phone | `+91 99000 30001` |
| Primary doctor | Dr. Priya Iyer |

#### Visit 1 — 2026-04-05 (Bronchiolitis)

- **Diagnosis**: Viral bronchiolitis, mild-moderate. SpO₂ 96% on room air.
- **Treatment plan**: Supportive care, saline nasal drops, monitor red-flag signs.
- **Notes**: 2y 5m old, weight 13 kg. No prior wheezing episodes.

**Medications**

| Name | Reason | Instructions | If missed |
| --- | --- | --- | --- |
| Paracetamol syrup 250 mg/5 mL | Fever | 5 mL every 6 h as needed | Skip; next dose as scheduled |
| Saline nasal drops | Nasal congestion | 2 drops each nostril 4×/day | No harm missing; resume |

**Tests** — none ordered; clinical diagnosis.

---

### 5. Mohammad Imran — self-registered, no doctor yet

| Field | Value |
| --- | --- |
| Email | `imran.m@example.com` |
| Password | `Patient#1` |
| DOB | 1992-01-18 |
| Gender | M |
| Phone | *(left blank on purpose, to demo optional phone)* |
| Primary doctor | *(none — will pick later)* |

Use this account to demo the **"patient without a doctor"** case: dashboard
shows the "No doctor assigned yet" badge, visits list is empty.

---

## Demo script — suggested flow (≈ 6 minutes)

1. Log in as **Dr. Arjun Menon** (cardiologist). Open Sundar Rao → show the
   two-visit history, full medication stack, and the recently added diuretic.
2. Log out, log in as **patient Sundar Rao**. Open the AI chat and ask:
   - *"Can I still take an occasional aspirin for a headache?"*
   - *"When should I call the doctor about ankle swelling?"*
   - *"What happens if I miss my morning metoprolol?"*
3. Log out, log in as **patient Mohammad Imran** to show a fresh, empty
   account — highlighting that phone is optional and no doctor is required.
4. Log in as **Dr. Meera Nair**, add a new visit for Rahul Deshpande live on
   stage to show the create-visit flow.

---

## Resetting between demos

Use the "wipe domain data, keep superuser" snippet from
[auth-refactor.md](auth-refactor.md#db-reset), then re-seed from this file.
