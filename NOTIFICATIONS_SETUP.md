# WhatsApp Notifications — Setup Guide

Wahabix Medicare Solution has WhatsApp notification **hooks** already
wired into the app at three points:

1. **Token issued** (Reception) → `apps/reception/views.py` → `token_create`
2. **Lab report ready** (Laboratory) → `apps/laboratory/views.py` → `result_entry`
3. **Prescription finalized** (Doctor) → `apps/doctor/views.py` → `prescription_create`

Right now, all three are **safe no-ops** — they log to Audit Logs
("[WhatsApp not configured] Would have sent to...") but don't actually
send anything, because sending a real WhatsApp message requires an
account only you can create (Meta/Twilio don't let anyone set this up
on your behalf without your business details and phone number).

## Why this couldn't be built "working" out of the box

A real WhatsApp integration needs:
- An approved **WhatsApp Business API** account (via Meta Cloud API
  directly, or a reseller like Twilio / Gupshup / 360dialog)
- A dedicated **phone number** registered to that account
- An **API token** issued to your account specifically
- Usually a short Meta business-verification process (can take a few
  days)

None of that exists yet for Wahabix Medicare Solution specifically —
it has to be *your* account, with *your* verified business and phone
number, not something that can be fabricated in code.

## Steps to go live

1. **Pick a provider:**
   - **Meta Cloud API** — free per-conversation pricing tiers, but more
     setup work: developers.facebook.com/docs/whatsapp/cloud-api
   - **Twilio** (or Gupshup/360dialog) — usually faster to get running,
     small per-message cost, better documentation for beginners:
     twilio.com/whatsapp

2. **Get your credentials** — API URL, access token, and the WhatsApp
   number you're approved to send from.

3. **Add them to `.env`:**
   ```
   WHATSAPP_API_URL=https://your-provider's-send-endpoint
   WHATSAPP_API_TOKEN=your-real-token
   WHATSAPP_FROM_NUMBER=+92XXXXXXXXXX
   ```

4. **Implement one function** — open
   `apps/core/services/notifications.py` and fill in
   `_send_via_provider()` to match your chosen provider's exact request
   format (they all differ slightly — Twilio uses one JSON shape, Meta
   Cloud API another). Everything else (audit logging, error handling,
   the three trigger points above) already works and doesn't need
   touching.

5. Test with `python manage.py shell`:
   ```python
   from apps.core.services.notifications import send_whatsapp
   send_whatsapp(to_phone="+92XXXXXXXXXX", message="Test message")
   ```

## What NOT to do

Don't hardcode a token directly into `notifications.py` or any template
— always use `.env` / environment variables, same as every other secret
in this app (see `REMOVE_BEFORE_PRODUCTION.md`).
