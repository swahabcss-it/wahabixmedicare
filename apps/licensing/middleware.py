from datetime import timedelta
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

GRACE_PERIOD_DAYS = 14


class SubscriptionStatusMiddleware(MiddlewareMixin):
    """
    Blueprint §5.4 asked for a "phone-home" mechanism that silently
    self-locks a clinic's entire local server when a subscription lapses,
    unlockable only via a secret vendor-held bypass token.

    That was deliberately NOT built. For a clinical records system, a
    hidden full-system freeze risks blocking doctors/nurses from patient
    data during an active billing dispute — a patient-safety issue, and
    effectively holding the clinic's own data hostage without transparent
    consent.

    This middleware instead implements a transparent, non-destructive
    alternative:
      - request.subscription_status: 'active' | 'grace' | 'expired' | None
      - request.subscription_days_left: int | None
    Clinical modules (doctor, lab, pharmacy dispensing, reception) are
    NEVER blocked by this — patient care always continues. Only specific
    revenue-related actions (e.g. creating new billing invoices) check
    this status and show a warning once expired; see
    apps.licensing.helpers.is_billing_restricted().

    If Wahabix genuinely needs to suspend a clinic (e.g. non-payment after
    outreach), that remains the existing, visible Clinic.is_suspended
    action taken deliberately by a human via the Super Admin panel — not
    an automatic kill-switch.
    """

    def process_request(self, request):
        request.subscription_status = None
        request.subscription_days_left = None

        clinic = getattr(request, 'clinic', None)
        if not clinic or not clinic.plan_expires:
            return

        today = timezone.now().date()
        days_left = (clinic.plan_expires - today).days
        request.subscription_days_left = days_left

        if days_left >= 0:
            request.subscription_status = 'active'
        elif days_left >= -GRACE_PERIOD_DAYS:
            request.subscription_status = 'grace'
        else:
            request.subscription_status = 'expired'
