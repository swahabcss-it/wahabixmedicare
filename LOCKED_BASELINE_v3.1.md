# Wahabix Medicare Solution — v3.1 LOCKED BASELINE

This marks the current feature set as **stable and locked**. Anything
listed here is considered done and working — future changes should be
additive (new features) rather than altering this locked behavior, unless
a real bug is found.

## Locked Core Flows
- **Reception → Invoice** — issuing a token with a fee auto-creates a
  matching Invoice and posts it to the Accounts ledger. Token = receipt.
- **Doctor → Lab → Reception Payment** — ordering lab tests from a
  prescription auto-creates an unpaid Invoice, collected later at
  Reception under "Pending Lab Payments", with full view/download
  available both before and after collection.
- **Reception Invoicing** — receptionists can view, create, and print/
  download any invoice directly (no Accountant login needed).
- **Pharmacy Sales** — Decimal-safe billing math (no more float/Decimal
  crashes).
- **Lab Test Catalog & Results Entry** — the `data-confirm` submit-button
  bug that silently blocked saving is fixed app-wide (Lab, Payroll,
  Insurance Claims all affected, all fixed).
- **Prescription Print (Letterhead style)** — matches hospital Rx
  letterhead format with Urdu dosage instructions support.
- **Token Print** — silent iframe print, no new tab / no manual "back".
- **Platform Theme** — Super-Admin-only, applies everywhere, no per-user
  override.
- **Security config** — env-based secrets, `ALLOWED_HOSTS` always
  includes local dev hosts regardless of `.env` content, cookie security
  decoupled from `DEBUG` (`USE_HTTPS_SECURE_COOKIES`).
- **Demo data** — 20 lab tests + 20 medicines with stock batches seeded
  via `python manage.py seed_demo_data`.

## UI — v3.1 Polish Layer
Visual refinements added on top of the existing 8-theme design system
(dark/light/ocean/emerald/rose/sepia/contrast/slate), all still controlled
solely by Super Admin → Platform Settings:
- Theme-tinted elevation (cards/stats glow with the active accent color
  instead of a flat gray shadow)
- Gradient underline on every card header (signature detail, repeated
  consistently)
- Sticky table headers for long lists
- Accent sweep-in on table row hover
- Sidebar active-link soft glow instead of a flat stripe
- Gradient-clipped stat numbers
- Radial-backdrop empty states
- Refined button press/disabled states
- Accent "kicker" bar on every page title

No markup/class names changed — this is a pure CSS layer
(`static/css/wms-theme.css`, bottom section marked "PREMIUM POLISH LAYER"),
so nothing above should have broken.

## If You Need To Change Something Here
That's fine — this document just means "known good as of this point,"
not "off-limits." If you do change locked behavior, update this file so
the baseline stays honest.
