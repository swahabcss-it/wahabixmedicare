# 🏥 Wahabix Medicare Solution
### Enterprise SaaS Clinic Management System

> **Developed & Designed by:** WAHABIX (Shah Abdul Wahab)  
> **Version:** 3.0 Production | **Year:** 2026  
> **Stack:** Django 5.x · Python 3.11+ · PostgreSQL (prod) / SQLite (dev) · Vanilla JS

---

## 🌟 Features

### Super Admin (SaaS Core)
- Multi-tenant clinic provisioning
- Granular module feature toggles per clinic
- Staff management across all tenants
- System-wide audit logs
- Subscription plan management (Basic / Professional / Enterprise)

### Reception Module
- Patient registration with full demographics
- Token queue system with vitals logging
- Daily patient flow management

### Laboratory Module
- Test catalog with configurable rates
- Lab order management with auto voucher codes
- Result entry with soft-delete guard

### Doctor Module
- Patient queue from reception
- Electronic Health Records (EHR)
- Prescription writing

### Pharmacy Module
- Medicine inventory management
- POS billing terminal
- Stock & expiry alerts

### HR & Payroll Module
- Employee directory
- Salary slip generation
- Deductions & bonus tracking

### Billing Module
- Invoice generation
- Payment tracking
- Balance sheet
- **Autonomous double-entry General Ledger** (auto-posts on every cleared invoice/sale)
- Insurance panel co-pay splitting & claims tracking

### Asset Management Module (New in v3.0)
- Equipment/furniture registry with asset tags & barcodes
- Straight-line depreciation (auto-calculated book value)
- Service/maintenance logs with overdue calibration alerts
- Warranty tracking

### Multi-Tenant Subdomain Routing (New in v3.0)
- Wildcard subdomain support (`clinicname.yourdomain.com`) via `BASE_DOMAIN` env var
- Public `GET /api/v1/tenant/initialize?subdomain=X` endpoint for white-labeled login branding
- Existing session-based Super Admin clinic switching still works unchanged

### Subscription & Licensing (New in v3.0)
Transparent, patient-safety-first approach:
- Clinics see a renewal banner during a 14-day grace period and after expiry
- **Clinical modules (Doctor, Lab, Pharmacy, Reception) are never blocked** — patient care is never interrupted by a billing lapse
- Only new invoice creation pauses after expiry, with a clear message to renew
- Suspending a clinic entirely remains a deliberate, visible action a human takes via the Super Admin panel (`Clinic.is_suspended`) — there is no hidden remote kill-switch or "phone-home" self-lock mechanism. For healthcare software this matters: a silent full-system freeze during a billing dispute could block access to patient records, which is a patient-safety risk we chose not to build.

---

## 🎨 Theme System

5 built-in themes, switchable live:

| Theme   | Style         |
|---------|---------------|
| 🌑 Dark    | Default dark  |
| ☀️ Light   | Clean light   |
| 🌊 Ocean   | Deep indigo   |
| 🌿 Emerald | Forest green  |
| 🌹 Rose    | Rose gold     |

Theme preference persists via `localStorage`.

---

## 🚀 Quick Start (Development)

```bash
# 1. Clone / unzip project
cd wahabix_medicare_solution

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

> ⚠️ The app now reads **all secrets and DEBUG/ALLOWED_HOSTS from environment
> variables** (`.env` file, or real env vars in production/Docker). It will
> refuse to start without `SECRET_KEY` set — this is intentional; previous
> versions shipped with a hardcoded secret key which is a serious security
> issue in any public repo or shared codebase.

---

## 🔐 Default Login Credentials

| Role         | Username    | Password   |
|--------------|-------------|------------|
| Super Admin  | wahabix     | Admin@123  |
| Doctor       | dr_ahmad    | Staff@123  |
| Lab Supervisor | lab_asif  | Staff@123  |
| Receptionist | rec_maria   | Staff@123  |
| Pharmacist   | pharma_ali  | Staff@123  |

> ⚠️ **Change all passwords in production!**

---

## 🐳 Docker Deployment

```bash
cp .env.example .env   # fill in real SECRET_KEY, ANALYZER_API_KEY, DB_PASSWORD etc.
docker-compose up -d
```

Runs on port **8000** with a real PostgreSQL backend — `DATABASE_URL` is now
actually read by `config/settings.py` via `dj-database-url` (previously the
Docker Compose env vars were defined but silently ignored by settings.py,
so the container ran on SQLite with `DEBUG=True` regardless — this is fixed).

---

## 📁 Project Structure

```
wahabix_medicare_solution/
├── config/                 # Django settings & main URLs
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/               # Base models, middleware, auth
│   ├── superadmin_panel/   # SaaS super admin
│   ├── reception/          # Patient & token management
│   ├── laboratory/         # Lab orders & results
│   ├── doctor/             # Doctor workspace
│   ├── pharmacy/           # Medicine & POS
│   ├── hr_payroll/         # Staff & salary
│   └── billing/            # Invoices & payments
├── templates/
│   ├── base/               # Master layout + login
│   ├── superadmin/         # SA templates
│   ├── reception/          # Reception templates
│   ├── lab/                # Lab templates
│   └── ...
├── static/
│   ├── css/wms-theme.css   # 5-theme engine
│   └── js/wms-app.js       # JS utilities
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🏗️ Architecture Highlights

- **Multi-tenant isolation** via `TenantBaseModel` + `TenantManager`
- **Soft-delete pattern** — no hard DELETEs on critical data
- **Audit trail** — every action logged with user, clinic, IP, timestamp
- **Feature flags** — per-clinic module enable/disable
- **Role-based access** — staff roles enforce view-level permissions
- **Theme engine** — CSS custom properties, 5 themes, zero JS frameworks
- **Security** — CSRF, session timeout, XSS filter, clickjacking protection

---

## 📞 Support

**Developed by:** WAHABIX (Shah Abdul Wahab)  
**Location:** Sialkot, Pakistan  
**Project:** Wahabix Medicare Solution v2.0
