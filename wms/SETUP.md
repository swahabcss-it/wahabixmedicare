# Wahabix Medicare Solution v2.2 — Setup Guide

## Quick Start (Fresh Deployment)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY, DEBUG=False

# 3. Database
python manage.py migrate
python manage.py seed_demo_data --password YourStrongPassword

# 4. Run
python manage.py runserver
```

## Login Accounts

| Username | Password | Role | Access |
|----------|----------|------|--------|
| `wahabix` | *(set via seed)* | **Super Admin** | `/superadmin/` — full SaaS control |
| `admin_medicare` | `ClinicAdmin@123` | **Clinic Admin** | `/clinic-admin/` — staff & profile mgmt |
| `dr_ahmad` | *(existing)* | Doctor | `/doctor/` only |
| `lab_asif` | *(existing)* | Lab Supervisor | `/lab/` only |
| `rec_maria` | *(existing)* | Receptionist | `/reception/` only |
| `pharma_ali` | *(existing)* | Pharmacist | `/pharmacy/` only |

---

## v2.2 Changes

### Bug Fixed ✅
- `ERR_TOO_MANY_REDIRECTS` permanently fixed via `core:home` role dispatcher

### New: Professional PDF Reports (5 types)
| Report | URL | Who |
|--------|-----|-----|
| Lab Result PDF | `/lab/orders/<pk>/pdf/` | Lab Supervisor |
| Prescription PDF | `/doctor/prescriptions/<pk>/pdf/` | Doctor |
| Pharmacy Invoice PDF | `/pharmacy/sales/<pk>/pdf/` | Pharmacist |
| Billing Invoice PDF | `/billing/invoices/<pk>/pdf/` | Accountant |
| Payroll Slip PDF | `/hr/payroll/<pk>/pdf/` | HR Manager |

All PDFs include clinic logo, professional branding, confidentiality footer, page numbers.

### Strict Role Isolation ✅
Each role sees and can access ONLY their own module:
- `receptionist` → `/reception/` only
- `doctor` → `/doctor/` only
- `lab_supervisor` → `/lab/` only
- `pharmacist` → `/pharmacy/` only
- `hr_manager` → `/hr/` only
- `accountant` → `/billing/` only
- `clinic_admin` → `/clinic-admin/` only (management, not operations)

Access to other modules is blocked at the HTTP level via `role_required` decorator,
not just hidden in the nav.

### OOP Architecture
`apps/core/services/pdf_service.py`:
- `BaseClinicPDF` — abstract base (header, footer, logo, layout)
- `LabReportPDF(BaseClinicPDF)`
- `PrescriptionPDF(BaseClinicPDF)`
- `PharmacyInvoicePDF(BaseClinicPDF)`
- `BillingInvoicePDF(BaseClinicPDF)`
- `PayrollSlipPDF(BaseClinicPDF)`

### Staff Password Reset ✅
- Super Admin: `/superadmin/staff/<pk>/edit/`
- Clinic Admin: `/clinic-admin/staff/<pk>/edit/`
