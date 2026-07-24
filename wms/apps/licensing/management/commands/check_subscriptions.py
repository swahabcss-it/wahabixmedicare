from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import Clinic
from apps.licensing.models import SubscriptionEvent


class Command(BaseCommand):
    """
    Run daily via cron: python manage.py check_subscriptions

    Purely informational. Logs a SubscriptionEvent for clinics entering
    their grace period or expiring, and prints a summary so Wahabix
    Support can follow up personally (call/email the clinic). This command
    NEVER modifies Clinic.is_suspended or blocks any access — suspension
    stays a deliberate human action in the Super Admin panel.
    """
    help = "Check clinic subscription expiries and log renewal reminders (does not lock anything)."

    def handle(self, *args, **options):
        today = timezone.now().date()
        expiring_soon = Clinic.objects.filter(
            is_active=True, plan_expires__isnull=False,
            plan_expires__gte=today, plan_expires__lte=today + timedelta(days=14),
        )
        just_expired = Clinic.objects.filter(
            is_active=True, plan_expires__isnull=False, plan_expires__lt=today,
        )

        for clinic in expiring_soon:
            SubscriptionEvent.objects.create(
                clinic=clinic, event_type='grace_period_started',
                plan_expires_at_event=clinic.plan_expires,
                notes=f'{(clinic.plan_expires - today).days} days remaining',
            )
            self.stdout.write(f"⏰ {clinic.name} expires {clinic.plan_expires} — reminder logged.")

        for clinic in just_expired:
            SubscriptionEvent.objects.create(
                clinic=clinic, event_type='expired',
                plan_expires_at_event=clinic.plan_expires,
            )
            self.stdout.write(f"⚠️  {clinic.name} expired on {clinic.plan_expires} — Support follow-up needed.")

        self.stdout.write(self.style.SUCCESS(
            f"Done. {expiring_soon.count()} expiring soon, {just_expired.count()} expired."
        ))
