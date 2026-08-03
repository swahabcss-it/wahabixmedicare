def is_billing_restricted(request) -> bool:
    """
    Only 'expired' (past grace period) soft-restricts NEW invoice creation
    — a nudge to renew, not a lockout. Reading existing invoices, patient
    records, lab results, and prescriptions is never affected.
    """
    return getattr(request, 'subscription_status', None) == 'expired'
