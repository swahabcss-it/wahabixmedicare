# ⚠️ REMOVE BEFORE PRODUCTION — Testing-Only Additions

This file exists so nothing gets forgotten when you're ready to go live.

## 1. Quick-Login Buttons on the Login Page
**File:** `templates/base/login.html`
- Search for `TESTING ONLY` — delete that entire block (buttons + `<script>`).
- These buttons auto-hide already when `DEBUG=False` in your `.env`, but
  don't rely on that alone — delete the block outright before any real
  deployment. Never leave working demo credentials anywhere near
  production, even hidden behind a flag.

## 2. Demo Data / Demo Accounts
- `python manage.py seed_demo_data` creates `wahabix / Demo@12345` plus
  role accounts (`admin_demo`, `doctor_demo`, etc.) all sharing the same
  password. Before production:
  - Delete these accounts from `/django-admin/` or via Super Admin panel, OR
  - At minimum, change every demo account's password to something unique.

## 3. `.env` File
- The shipped `.env` has `DEBUG=True` and a placeholder `SECRET_KEY` —
  fine for local testing, **not fine for production**. Before deploying:
  - Set `DEBUG=False`
  - Generate a real `SECRET_KEY`:
    `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
  - Set a real `ANALYZER_API_KEY` if using the lab analyzer webhook
  - Set `ALLOWED_HOSTS` to your real domain(s)

## 4. Windows Installer Password
- If you're using the generated installer, remember its admin password
  is whatever you set in `installer/wms_installer.iss` (`AdminPassword`)
  — this only gates the *installer wizard*, not the running application.
  It has nothing to do with application login security.
