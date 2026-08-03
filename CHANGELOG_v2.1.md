# Wahabix Medicare Solution — v2.1 Patch Notes

## Bug Fixes

### ERR_TOO_MANY_REDIRECTS — FIXED ✅
**Root cause:** `login_view` always redirected every authenticated user to
`/superadmin/dashboard/`. That view is gated to `is_superuser`, so every
clinic staff member was bounced back to `/auth/login/`, which again redirected
to `/superadmin/dashboard/`, looping forever.

**Fix:** Created `core:home` — a single role-aware dispatcher view that sends
each user to *their* dashboard based on `staff_role`. Login, logout, the logo
link, and all "go home" redirects now point here instead of hardcoding
`superadmin:dashboard`.

---

## New: Clinic Admin Module (`/clinic-admin/`) ✅
The SRS required it; it was completely missing from v2.

| Feature | URL |
|---|---|
| Dashboard with stats & audit trail | `/clinic-admin/dashboard/` |
| Staff list | `/clinic-admin/staff/` |
| Add staff | `/clinic-admin/staff/create/` |
| **Edit staff / reset password** | `/clinic-admin/staff/<pk>/edit/` |
| Clinic profile edit | `/clinic-admin/profile/` |

Clinic admins can change any staff member's name, username, email, phone,
CNIC, role, active status, and password. The password field is optional on
edit — leave blank to keep the current password.

---

## New: Super Admin Staff Edit + Password Reset ✅
`/superadmin/staff/<pk>/edit/` — full edit form matching clinic_admin/staff_form.html.
Password field is optional: blank = keep current password.

---

## Full Module Implementations ✅
All "coming soon" stubs replaced with working views and templates:

| Module | New Features |
|---|---|
| **Doctor** | Live queue, call patient in, prescription writer with medicines table, prescription history |
| **Laboratory** | Role_required guard, test catalog with permission-gated soft-delete button, result entry form |
| **Pharmacy** | Medicine stock CRUD, POS sale form, stock quantity auto-deduction on sale |
| **HR & Payroll** | Employee roster, payroll slip generation with per-employee adjustments |
| **Billing** | Invoice creation with line items, tax/discount, partial payment tracking |

---

## Architecture Fixes
- `TenantMiddleware` — exempt list expanded; no more redirect loops for `/home/` and `/clinic-admin/`
- `role_required` decorator — replaces 3 different inline `clinic_required` implementations across apps
- Context processor — `nav_show_*` flags now use role+flag logic; clinic_admin sees all enabled modules
- Superadmin login/logout dead code removed from `superadmin_panel/views.py`
- All `@clinic_required` decorators in reception replaced with `@role_required`

---

## Seed Accounts (existing database)

| Username | Password | Role | Clinic |
|---|---|---|---|
| `wahabix` | *(existing)* | Super Admin | — |
| `admin_medicare` | `ClinicAdmin@123` | Clinic Admin | Medicare Plus Lahore |
| `dr_ahmad` | *(existing)* | Doctor | Medicare Plus Lahore |
| `lab_asif` | *(existing)* | Lab Supervisor | Medicare Plus Lahore |
| `rec_maria` | *(existing)* | Receptionist | Medicare Plus Lahore |
| `pharma_ali` | *(existing)* | Pharmacist | Medicare Plus Lahore |

For fresh PostgreSQL deployments run:
```
python manage.py seed_demo_data --password YourPassword
```
