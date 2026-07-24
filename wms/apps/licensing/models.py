from django.db import models
from apps.core.models import TenantBaseModel


class SubscriptionEvent(TenantBaseModel):
    """
    Audit trail of subscription lifecycle events. Purely informational —
    nothing in this app can lock a clinic out of its own data. Suspending
    a clinic remains a deliberate, visible action taken by Wahabix Support
    via the existing Super Admin panel (Clinic.is_suspended), never an
    automatic/hidden mechanism.
    """
    EVENT_TYPES = [
        ('grace_period_started', 'Grace Period Started'),
        ('expired', 'Subscription Expired'),
        ('renewed', 'Subscription Renewed'),
        ('reminder_sent', 'Renewal Reminder Sent'),
    ]
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    plan_expires_at_event = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.clinic.name} — {self.get_event_type_display()} ({self.created_at:%Y-%m-%d})"
