# Wahabix Medicare Solution — QA Audit Report (v3.3)

Full systematic pass across the entire codebase. Everything below was
actually checked programmatically, not just eyeballed.

## ✅ Passed Clean

| Check | Result |
|---|---|
| Python syntax (all 130+ files) | ✅ No errors |
| Django template tag balance (`if`/`for`/`block`/`with`) | ✅ Balanced everywhere |
| CSS brace balance | ✅ Balanced |
| Every `{% url %}` reference resolves to a real URL name | ✅ 183 references checked, 0 broken |
| Tenant isolation (`clinic=request.clinic` on every `get_object_or_404`) | ✅ Confirmed on all clinic-scoped views; Super Admin views correctly exempt (by design — operates across clinics) |
| Every POST `<form>` has `{% csrf_token %}` | ✅ 0 missing |
| `data-confirm` on submit buttons actually submits the form | ✅ Fixed earlier, re-confirmed still correct |
| `INSTALLED_APPS` matches every folder in `apps/` | ✅ Exact match |
| Migration dependency graph | ✅ No dangling/broken references |
| `role_required()` role names match `StaffProfile.ROLES` | ✅ No typos |
| `feature_flag=` names match real `Clinic` boolean fields | ✅ No typos |
| Every `render()` template path exists on disk | ✅ 0 missing |
| Print buttons use inline PDF URL, not `?download=1` (which would print blank) | ✅ Confirmed |
| No hardcoded secrets/passwords in source | ✅ Clean |
| No stray `print()` debug statements | ✅ Clean |

## 🔧 Fixed During This Pass

1. **`apps/assets/models.py`** — `age_years` used `Decimal(365.25)` (constructing
   a Decimal directly from a float literal), which silently carries tiny
   binary floating-point imprecision into the Decimal. Not a crash, but
   not correct either. Changed to `Decimal('365.25')` (string construction
   — the correct way to get an exact Decimal).

## Already Fixed In Earlier Rounds (Re-Verified Still Correct)

- Pharmacy sale Decimal/float crash (`sale.total = max(0, subtotal - discount)`)
- `data-confirm` silently not submitting forms (Lab results, Payroll, Claims)
- `ALLOWED_HOSTS` always includes local dev hosts regardless of `.env`
- `STORAGES["default"]` missing (broke all file uploads/logos)
- Cookie security decoupled from `DEBUG` (`USE_HTTPS_SECURE_COOKIES`)
- Sticky `<thead>` CSS bug (was overlapping header with first row) — removed
- Token/Invoice/Lab-payment linking, reception invoicing module
- Static asset cache-busting (`?v={{ APP_VERSION }}`)

## Not Independently Verifiable Here

This sandbox has no network access and Django isn't installed in it, so I
cannot actually run `python manage.py check`, `makemigrations --check`, or
the dev server itself. Everything above was verified via direct source
inspection and small analysis scripts instead of a live Django run. If you
want the strongest possible guarantee, run this locally and share any
traceback:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
```

The second command should print "No changes detected" — if it doesn't,
that means some model field doesn't yet have a matching migration.
