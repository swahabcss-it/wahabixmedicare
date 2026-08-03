# Wahabix Medicare Solution — v3.0 Release Notes

Built against the "Enterprise Clinic Management SaaS Platform" architectural
blueprint. Summary of what changed and why.

## 🔒 Security & Config (Critical Fixes)
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `ANALYZER_API_KEY` now come from
  environment variables via `python-decouple`. The app **refuses to start**
  without a real `SECRET_KEY` — no more hardcoded production secret shipped
  in source control.
- `DATABASE_URL` is now actually wired up via `dj-database-url`. Previously
  `docker-compose.yml` declared Postgres env vars that `settings.py` never
  read, so Docker deployments silently ran on SQLite with `DEBUG=True`.
  Fixed — Postgres is used automatically when `DATABASE_URL` is set.
- `whitenoise` added for static file serving, HSTS/secure-cookie settings
  now auto-harden when `DEBUG=False`.
- Login brute-force throttling added (`LOGIN_ATTEMPT_LIMIT` /
  `LOGIN_ATTEMPT_WINDOW_SECONDS`), failed attempts logged to `AuditLog`.
- Minimum password length raised 8 → 10.

## 🌐 Multi-Tenant Subdomain Routing (Blueprint §2)
- `SubdomainTenantMiddleware` resolves a clinic from `*.{BASE_DOMAIN}` for
  white-labeled branding, without touching the existing session-based
  Super-Admin clinic-switching flow.
- Public read-only `GET /api/v1/tenant/initialize?subdomain=X` endpoint
  returns clinic name/logo/enabled-modules/subscription-status only —
  no patient or staff data, no auth bypass.

## 🛠️ New: Asset Management Module (Blueprint §4E)
- `apps.assets`: equipment/furniture registry, asset tags, straight-line
  depreciation with auto-calculated book value, service/maintenance logs,
  overdue-calibration alerts, warranty tracking.
- New Super Admin feature flag: `is_assets_enabled`.

## 💰 Accounts / Double-Entry Ledger (Blueprint §4E)
- Already existed in `apps.billing.LedgerEntry` — confirmed it matches the
  blueprint's double-entry, auto-posting design. No changes needed here.

## 🪪 Subscription & Licensing (Blueprint §5.4 — reworked)
The blueprint's original spec called for a hidden phone-home mechanism that
could silently freeze a clinic's entire local server, unlockable only via a
secret vendor-held bypass token.

**We did not build that.** For a system holding patient medical records, a
covert full-system lockout during a billing dispute risks blocking doctors
and nurses from active patient data — a genuine patient-safety issue, and
effectively holds the clinic's own data hostage without transparent consent.

Instead, `apps.licensing` implements:
- A transparent renewal banner shown to clinic admins during a 14-day grace
  period and after expiry.
- Clinical modules (Doctor, Lab, Pharmacy, Reception) are **never** blocked.
- Only new invoice creation pauses after expiry, with a clear on-screen
  explanation and a path to renew.
- `manage.py check_subscriptions` — a daily cron-friendly command that logs
  expiring/expired clinics for Wahabix Support to follow up personally. It
  never modifies `Clinic.is_suspended` itself.
- Actually suspending a clinic remains the existing, visible, human-driven
  action in the Super Admin panel — unchanged from v2.

## 🆔 UUID Identifiers (Blueprint §3, pragmatic version)
The blueprint's schema used UUID primary keys throughout. Converting every
existing integer PK across 9 apps' foreign keys would be a high-risk,
all-or-nothing migration with no functional benefit for internal joins.

Instead, `Clinic.public_id` (UUID) was added as the identifier exposed to
any external system (the tenant-initialize API, future webhooks/QR codes),
while internal PKs stay `BigAutoField` for simple, fast joins. This gives
the actual security benefit the blueprint wanted (no guessable sequential
IDs in public-facing surfaces) without the schema-wide rewrite risk.

## ⚠️ Not Implemented (by design)
- **Code obfuscation / binary compilation for on-premise deployments**:
  reasonable to pursue for IP protection, but not done as part of this pass.
  Docker image distribution (already supported) is the recommended and more
  reliable way to keep on-premise source out of client hands.
