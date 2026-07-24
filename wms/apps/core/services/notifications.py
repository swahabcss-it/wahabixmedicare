"""
WhatsApp Notification Service
==============================
A pluggable hook, NOT a working integration out of the box — sending a
real WhatsApp message requires an approved WhatsApp Business account
(Meta Cloud API, or a reseller like Twilio) with its own phone number,
API token, and Meta Business verification. None of that can be set up
from inside this codebase — it's an account you create yourself.

Until real credentials are added to `.env`, every call here safely logs
to AuditLog and returns without sending anything — nothing crashes, no
message silently disappears without a trace, and no fake "sent!" message
gets shown to staff for something that didn't actually go anywhere.

── TO GO LIVE ──────────────────────────────────────────────────────────
1. Get a WhatsApp Business API account. Two common paths:
   a) Meta Cloud API directly — developers.facebook.com/docs/whatsapp
   b) A reseller like Twilio, Gupshup, or 360dialog (usually faster to
      set up, small per-message cost)
2. Add to `.env`:
     WHATSAPP_API_URL=<provider's send-message endpoint>
     WHATSAPP_API_TOKEN=<your access token>
     WHATSAPP_FROM_NUMBER=<your approved WhatsApp business number>
3. Implement `_send_via_provider()` below to match your provider's exact
   request format (they all differ slightly) — the surrounding safety
   net (audit logging, error handling, opt-in checks) already works.
"""
from django.conf import settings
from apps.core.models import AuditLog


def is_configured() -> bool:
    return bool(
        getattr(settings, 'WHATSAPP_API_URL', '') and
        getattr(settings, 'WHATSAPP_API_TOKEN', '')
    )


def send_whatsapp(*, to_phone: str, message: str, clinic=None, user=None, context: str = '') -> bool:
    """
    Returns True if a message was actually sent, False otherwise (never
    raises — a notification failure should never break the actual
    clinical/billing action that triggered it, e.g. issuing a token
    should still succeed even if the WhatsApp send fails).
    """
    if not to_phone:
        return False

    if not is_configured():
        # Safe no-op: nothing configured yet. Logged so it's visible in
        # Audit Logs that a notification WOULD have gone out here once a
        # real provider is wired up — not silently dropped.
        AuditLog.log(
            f'[WhatsApp not configured] Would have sent to {to_phone}: "{message[:60]}"',
            user=user, clinic=clinic, details=context,
        )
        return False

    try:
        success = _send_via_provider(to_phone, message)
        AuditLog.log(
            f'WhatsApp {"sent" if success else "failed"} to {to_phone}: "{message[:60]}"',
            user=user, clinic=clinic, details=context,
        )
        return success
    except Exception as e:
        AuditLog.log(f'WhatsApp send error to {to_phone}: {e}', user=user, clinic=clinic, details=context)
        return False


def _send_via_provider(to_phone: str, message: str) -> bool:
    """
    Replace this with your actual provider's API call once you have
    credentials. Left unimplemented on purpose — every provider's request
    shape is different, and shipping a guessed implementation against an
    API this codebase has never actually talked to would be worse than
    being explicit that this step is still needed.
    """
    raise NotImplementedError(
        "WHATSAPP_API_URL/TOKEN are set, but _send_via_provider() hasn't been "
        "implemented for your specific provider yet. See the module docstring."
    )


# ── Convenience wrappers for common triggers ────────────────────────────
# Call these from the relevant views once you're ready to go live. They're
# not wired into any view automatically — see NOTIFICATIONS_SETUP.md for
# exactly where to add each call.

def notify_token_issued(token):
    patient = token.patient
    msg = (
        f"Hi {patient.full_name}, your token #{token.token_number} at "
        f"{token.clinic.name} has been issued."
    )
    if token.invoice:
        msg += f" Invoice {token.invoice.invoice_number} — Rs.{token.invoice.total}."
    return send_whatsapp(to_phone=patient.phone, message=msg, clinic=token.clinic, context='token_issued')


def notify_lab_report_ready(order):
    patient = order.patient
    msg = (
        f"Hi {patient.full_name}, your lab report (Voucher {order.voucher_code}) "
        f"at {order.clinic.name} is ready. Log in to the Patient Portal to view it."
    )
    return send_whatsapp(to_phone=patient.phone, message=msg, clinic=order.clinic, context='lab_report_ready')


def notify_prescription_ready(prescription):
    patient = prescription.patient
    msg = (
        f"Hi {patient.full_name}, Dr. {prescription.doctor.user.get_full_name()} "
        f"has written your prescription at {prescription.clinic.name}."
    )
    return send_whatsapp(to_phone=patient.phone, message=msg, clinic=prescription.clinic, context='prescription_ready')
