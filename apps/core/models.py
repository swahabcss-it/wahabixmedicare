from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class PlatformSettings(models.Model):
    """
    Singleton (always pk=1). Global settings controlled ONLY by Super Admin.
    Theme used to be a per-user localStorage toggle anyone could change —
    now it's a deliberate platform-wide setting, applied to every clinic
    and the login page identically.
    """
    THEMES = [
        ('dark', 'Dark'), ('light', 'Light'), ('ocean', 'Ocean'),
        ('emerald', 'Emerald'), ('rose', 'Rose'), ('sepia', 'Sepia'),
        ('contrast', 'High Contrast'), ('slate', 'Slate'),
    ]
    theme = models.CharField(max_length=20, choices=THEMES, default='dark')
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        from django.core.cache import cache
        cache.delete('platform_settings_theme')

    def delete(self, *args, **kwargs):
        pass  # singleton — never actually deletable

    @classmethod
    def get(cls):
        from django.core.cache import cache
        cached = cache.get('platform_settings_theme')
        if cached:
            return cached
        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set('platform_settings_theme', obj, timeout=300)
        return obj

    def __str__(self):
        return f"Platform Settings (theme={self.theme})"


class Clinic(models.Model):
    """Master tenant model — every clinic is an isolated tenant"""
    # Internal PK stays a fast BigAutoField for efficient joins across 9 apps.
    # public_id is what gets exposed externally (APIs, QR codes, webhooks)
    # so internal row counts/sequence are never guessable — this gives the
    # blueprint's "UUID for external identification" benefit without the
    # high-risk, all-app-breaking migration of converting every FK to UUID.
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='clinic_logos/', null=True, blank=True)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True)
    address = models.TextField()

    # SaaS Feature Flags
    is_lab_enabled = models.BooleanField(default=True)
    is_pharmacy_enabled = models.BooleanField(default=True)
    is_hr_enabled = models.BooleanField(default=True)
    is_reception_enabled = models.BooleanField(default=True)
    is_doctor_enabled = models.BooleanField(default=True)
    is_billing_enabled = models.BooleanField(default=True)
    is_assets_enabled = models.BooleanField(default=True)

    # Super-Admin-controlled: which sub-modules within each enabled
    # top-level module this clinic's subscription actually includes.
    # Shape: {"lab": {"result_entry": true, "stock_requests": false}, ...}
    # Missing keys default to True (see apps.core.submodules registry).
    submodule_map = models.JSONField(default=dict, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)

    # Subscription
    plan = models.CharField(max_length=50, choices=[
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ], default='professional')
    plan_expires = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clinic"
        verbose_name_plural = "Clinics"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_plan_active(self):
        if not self.plan_expires:
            return True
        return self.plan_expires >= timezone.now().date()

    def enabled_modules(self):
        # Second tuple element is now an icon KEY (rendered via the
        # {% icon %} template tag — apps.core.templatetags.icons), not a
        # raw emoji character, as part of the professional-UI pass.
        mods = []
        if self.is_lab_enabled: mods.append(('lab', 'lab', 'Laboratory'))
        if self.is_pharmacy_enabled: mods.append(('pharmacy', 'pharmacy', 'Pharmacy'))
        if self.is_hr_enabled: mods.append(('hr', 'hr', 'HR & Payroll'))
        if self.is_reception_enabled: mods.append(('reception', 'reception', 'Reception'))
        if self.is_doctor_enabled: mods.append(('doctor', 'doctor', 'Doctor'))
        if self.is_billing_enabled: mods.append(('billing', 'billing', 'Billing'))
        if self.is_assets_enabled: mods.append(('assets', 'assets', 'Assets'))
        return mods


class TenantManager(models.Manager):
    """Default manager — excludes soft-deleted records"""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def for_clinic(self, clinic):
        return self.get_queryset().filter(clinic=clinic)


class TenantBaseModel(models.Model):
    """
    Abstract base for ALL tenant data models.
    Provides: tenant isolation, soft-delete, audit timestamps.
    """
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set'
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_created'
    )

    objects = TenantManager()
    all_objects = models.Manager()  # Includes soft-deleted

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.save(update_fields=['is_deleted', 'updated_at'])

    def restore(self):
        self.is_deleted = False
        self.save(update_fields=['is_deleted', 'updated_at'])


class StaffProfile(models.Model):
    """Clinic staff linked to Django User"""
    ROLES = [
        ('clinic_admin', 'Clinic Admin'),
        ('doctor', 'Doctor'),
        ('lab_supervisor', 'Lab Supervisor'),
        ('pharmacist', 'Pharmacist'),
        ('receptionist', 'Receptionist'),
        ('hr_manager', 'HR Manager'),
        ('accountant', 'Accountant'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='staff')
    role = models.CharField(max_length=30, choices=ROLES, help_text='Primary role — decides their main dashboard/home screen')
    # Lets one person also work inside other modules (e.g. a Receptionist
    # who's also trusted to help in the Lab) without changing their
    # primary role/dashboard. Stored as comma-separated role keys.
    extra_roles = models.CharField(
        max_length=200, blank=True,
        help_text='Comma-separated additional roles this person can also access (multi-module access)'
    )
    phone = models.CharField(max_length=20, blank=True)
    cnic = models.CharField(max_length=15, blank=True, verbose_name='CNIC')
    avatar = models.ImageField(upload_to='staff_avatars/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # Permission flags — granted per-specific-person by Clinic Admin/Super
    # Admin, independent of role. A role alone never implies these.
    can_delete_lab_results = models.BooleanField(default=False)
    can_edit_lab_catalog = models.BooleanField(
        default=False,
        help_text="Lets this person add/edit/remove tests in the Lab Test Catalogue (prices, reference "
                   "ranges, turnaround times). Separate from result-deletion rights on purpose — someone "
                   "trusted to key in results isn't automatically trusted to change what a test costs or "
                   "its clinical reference range."
    )
    can_access_billing = models.BooleanField(
        default=False,
        help_text="Lets this person view/create/print invoices (e.g. a receptionist or lab staffer "
                   "handling walk-in payments) without giving them full Accountant/ledger access. "
                   "Accountants always have full billing access regardless of this flag."
    )
    joined_at = models.DateField(auto_now_add=True)

    # Clinic-Admin-controlled: within whatever the clinic's subscription
    # allows (Clinic.submodule_map), which specific sub-modules THIS staff
    # member is assigned. Same shape as Clinic.submodule_map. A key absent
    # here means OFF for this staff member (opt-in, unlike the clinic-level
    # default-on) — a new hire starts with nothing until explicitly granted.
    enabled_submodules = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Staff Profile"

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.get_role_display()}"

    def get_extra_roles_list(self) -> list:
        return [r.strip() for r in self.extra_roles.split(',') if r.strip()]

    def get_all_roles(self) -> list:
        """Primary role + any extra module access, deduplicated."""
        roles = [self.role] + self.get_extra_roles_list()
        seen = []
        for r in roles:
            if r not in seen:
                seen.append(r)
        return seen


class AuditLog(models.Model):
    """System-wide audit trail"""
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.user} — {self.action}"

    @classmethod
    def log(cls, action, user=None, clinic=None, model_name='', object_id=None, details='', request=None):
        ip = None
        if request:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')
        cls.objects.create(
            action=action, user=user, clinic=clinic,
            model_name=model_name, object_id=object_id,
            details=details, ip_address=ip
        )
