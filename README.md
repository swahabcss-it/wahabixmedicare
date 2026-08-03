# 🏥 Wahabix Medicare — Version 10 Complete
### Enterprise SaaS Clinic & Diagnostic Management System

> **Developed & Designed by:** Wahabix (Shah Abdul Wahab)
> **Stack:** Django 5.x · Python 3.11+ · PostgreSQL (prod) / SQLite (dev) · Vanilla JS, zero frontend framework

---

## What this is

A multi-tenant SaaS platform for clinics and diagnostic centers: one Super
Admin panel provisions and licenses clinics, each Clinic Admin manages their
own staff and module access, and every clinical/financial workflow —
reception, doctor consultation, lab, pharmacy, billing, HR, assets — runs
under a strict three-layer permission model so nothing is accessible by
default that hasn't been explicitly granted.

Insurance/TPA module exists in the codebase (`apps/insurance` equivalent
inside `billing`) but is **intentionally paused** for this build phase —
not wired into the main workflows yet.

---

## Three-Layer Permission Model

This is the core design principle of the whole platform, and it applies
everywhere:

1. **Super Admin (subscription layer)** — decides which top-level modules
   a clinic's plan includes (`Clinic.is_lab_enabled`, `is_pharmacy_enabled`,
   etc.), and — new in this build — exactly which **sub-modules** within
   each module are included (`Clinic.submodule_map`). E.g. a clinic can have
   Laboratory enabled but without Stock Requests, if that's not in their plan.
2. **Clinic Admin (staff assignment layer)** — from whatever the clinic's
   subscription allows, decides which specific sub-modules each staff
   member is actually assigned (`StaffProfile.enabled_submodules`). A new
   hire starts with nothing until explicitly granted — opt-in, not opt-out.
3. **Action-level flags** — fine-grained booleans for specific sensitive
   actions, independent of module/sub-module access:
   - `can_delete_lab_results` — delete a patient's lab order/result
   - `can_edit_lab_catalog` — add/edit/remove tests in the master Lab Test
     Catalogue (prices, reference ranges) — **deliberately a separate flag**
     from result deletion, since trusting someone to key in a result isn't
     the same as trusting them to change what a test costs
   - `can_access_billing` — view/manage financial records

A user's effective access is always the **intersection** of all three
layers, enforced server-side on every view (never just hidden in the UI).

---

## Module List

| Module | Key Features |
|---|---|
| **Super Admin** | Multi-tenant clinic provisioning, module + sub-module toggles per clinic, subscription/licensing management, platform-wide audit log, staff oversight across all tenants |
| **Clinic Admin** | Staff creation & role assignment, per-staff sub-module toggle screen, sensitive-action permission grants, clinic-scoped dashboard |
| **Reception** | Patient registration (full demographics), live token queue, vitals logging, cash shift management |
| **Doctor / OPD** | Token-based patient queue, Electronic Health Record (EHR) view, prescription writing, routes tests directly to Lab/Radiology and medicines to Pharmacy |
| **Laboratory** | Test catalogue (authorization-gated editing — see below), sample collection tracking, result entry with **auto Normal/Abnormal detection**, QR-verified locked reports, consumables stock requests |
| **Pharmacy** | Prescription-linked dispensing, walk-in POS sale, batch/expiry inventory, near-expiry alerts |
| **Billing & Accounts** | Invoice generation, payment collection with void/audit trail, autonomous double-entry general ledger (auto-posts on every cleared invoice/sale), balance sheet / P&L |
| **HR & Payroll** | Employee directory, attendance, leave management, salary slip generation |
| **Asset Management** | Equipment/furniture registry with asset tags, straight-line depreciation, service/calibration logs with overdue alerts, stock requisition approval |
| **Patient Portal** | Patients view their own reports, prescriptions, and invoices — nothing else |

---

## Laboratory: Auto Normal/Abnormal Detection (new)

While entering a result, the system parses the test's reference range
(`"70-110"`, `"<200"`, `">40"`, etc.) and the entered value live in the
browser, and shows a suggested **Normal / Abnormal** badge instantly —
pre-checking the Abnormal checkbox, which stays fully editable.

This is deliberately conservative for patient safety: if the reference
range is qualitative ("Negative/Positive") or doesn't parse cleanly, **it
does not guess** — the lab tech makes the call manually, same as before.
The moment a tech manually toggles the checkbox, the auto-logic stops
touching that row, so a human correction is never silently overwritten.

Logic lives in `apps/laboratory/range_utils.py`, unit-tested against 11
realistic value/range combinations including numeric ranges, one-sided
bounds, and qualitative values that must NOT be auto-flagged.

---

## Subscription & Licensing — a deliberate design decision

Documented in `apps/licensing` because it matters for a clinical system:
- Clinics see a renewal banner during a grace period and after expiry.
- **Clinical modules (Doctor, Lab, Pharmacy, Reception) are never blocked**
  by a billing lapse — patient care is never interrupted over payment status.
- Only new invoice creation pauses after expiry.
- Suspending a clinic entirely is a deliberate, visible action a human
  takes in the Super Admin panel (`Clinic.is_suspended`). There is no
  hidden remote kill-switch or "phone-home" self-lock — a silent full
  freeze during a billing dispute could block access to patient records,
  which is a patient-safety risk this project chose not to build.

---

## Theme / Layout System — status

⚠️ **Currently mid-rebuild.** The previous approach (8 palette presets —
Dark/Light/Ocean/Emerald/Rose/Sepia/Contrast/Slate, one CSS-variable swap
applied platform-wide) is being replaced with genuinely distinct,
**structurally different layout themes** (sidebar-nav vs. topbar-nav,
card-density vs. dense-table density, different template sets per theme —
closer to how WordPress themes work), selectable per-clinic by Super Admin
rather than a single global palette. This section will be updated as each
theme ships.

---

## Quick Start (Development)

```bash
# 1. Unzip project
cd wahabix_medicare_v10_complete

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set a real SECRET_KEY:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 5. Run migrations
python manage.py migrate

# 6. Seed demo data (optional)
python manage.py seed_demo_data

# 7. Run development server
python manage.py runserver

# 8. Visit: http://127.0.0.1:8000
```

> The app reads **all secrets and DEBUG/ALLOWED_HOSTS from environment
> variables** (`.env`, or real env vars in production/Docker) and refuses
> to start without `SECRET_KEY` set. `.env` is gitignored — only
> `.env.example` (placeholders, no real values) is committed.

---

## Default Login Credentials (after `seed_demo_data`)

| Role | Username | Password |
|---|---|---|
| Super Admin | wahabix | Admin@123 |
| Doctor | dr_ahmad | Staff@123 |
| Lab Supervisor | lab_asif | Staff@123 |
| Receptionist | rec_maria | Staff@123 |
| Pharmacist | pharma_ali | Staff@123 |

> ⚠️ **Change all passwords before any real deployment.**

---

## Docker Deployment

```bash
cp .env.example .env   # fill in real SECRET_KEY, ANALYZER_API_KEY, DB_PASSWORD etc.
docker-compose up -d
```

Runs on port **8000** against a real PostgreSQL backend (`DATABASE_URL`
read via `dj-database-url`).

---

## Project Structure

```
wahabix_medicare_v10_complete/
├── config/                 # Django settings & main URLs
├── apps/
│   ├── core/                # Base models, TenantBaseModel, AuditLog,
│   │                         #   StaffProfile, submodule registry, icons
│   ├── superadmin_panel/    # Platform-level control center
│   ├── clinic_admin/        # Per-clinic staff & access management
│   ├── licensing/           # Subscription/suspension logic (see above)
│   ├── reception/           # Patient registration & token queue
│   ├── doctor/               # EHR & prescriptions
│   ├── laboratory/          # Test catalogue, orders, results, auto-flag
│   ├── pharmacy/            # Dispensing, POS, inventory
│   ├── billing/             # Invoices, ledger, payments
│   ├── hr_payroll/          # Staff & salary
│   ├── assets/              # Equipment, depreciation, service logs
│   └── patient_portal/      # Patient-facing views
├── templates/
│   ├── base/                 # Master layout + login
│   └── ...                   # One folder per app above
├── static/
│   ├── css/wms-theme.css     # Being replaced by per-theme layout sets
│   └── js/wms-app.js
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Architecture Highlights

- **Multi-tenant isolation** via `TenantBaseModel` + `TenantManager`
- **Soft-delete pattern** — no hard DELETEs on clinical/financial data
- **Full audit trail** — every sensitive action logged with user, clinic, IP, timestamp
- **Three-layer permission model** — see above; enforced server-side, not just hidden UI
- **Security** — CSRF, session timeout, XSS filtering, clickjacking protection, no hardcoded secrets

---

## Pushing to GitHub

```bash
git init
git add .
git commit -m "Wahabix Medicare v10 Complete"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

Before pushing publicly, double-check:
- `.env` is **not** staged (`git status` should not list it — `.gitignore` already excludes it)
- Demo credentials above are rotated before any real clinic data touches this instance
- `DEBUG=False` and a real `SECRET_KEY` are set for any deployed environment

---

## License

Proprietary — © Wahabix (Shah Abdul Wahab). All rights reserved unless a
`LICENSE` file stating otherwise is added to this repository.

---

## Support

**Developed by:** Wahabix (Shah Abdul Wahab)
**Location:** Sialkot, Pakistan
**Project:** Wahabix Medicare Solution — Version 10 Complete
