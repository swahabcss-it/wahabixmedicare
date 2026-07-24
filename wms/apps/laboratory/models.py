import uuid
from django.db import models
from apps.core.models import TenantBaseModel
from apps.reception.models import Patient


class LabTestCatalog(TenantBaseModel):
    CATEGORIES = [
        ('clinical_chemistry', 'Clinical Chemistry'),
        ('haematology', 'Haematology'),
        ('microbiology', 'Microbiology'),
        ('serology', 'Serology / Immunology'),
        ('radiology', 'Radiology'),
        ('cardiology', 'Cardiology'),
        ('other', 'Other'),
    ]
    test_name = models.CharField(max_length=255)
    test_code = models.CharField(max_length=50)
    category = models.CharField(max_length=30, choices=CATEGORIES, default='clinical_chemistry')
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    reference_range = models.TextField()
    unit = models.CharField(max_length=50, blank=True)
    sample_type = models.CharField(max_length=100, blank=True, help_text="e.g. Blood, Urine, Stool")
    turnaround_hours = models.PositiveIntegerField(default=24)

    class Meta:
        ordering = ['test_name']

    def __str__(self):
        return f"{self.test_name} [{self.test_code}] — Rs.{self.rate}"


class LabOrder(TenantBaseModel):
    STATUS = [('pending','Pending'),('processing','Processing'),('completed','Completed'),('delivered','Delivered')]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_orders')
    tests = models.ManyToManyField(LabTestCatalog, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    doctor_name = models.CharField(max_length=255, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    voucher_code = models.CharField(max_length=20, unique=True)
    verification_hash = models.CharField(max_length=32, unique=True, blank=True, help_text='Encoded into report QR code for tamper-proof verification')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    ordered_at = models.DateTimeField(auto_now_add=True)
    # Auto-created the moment a doctor orders these tests (see
    # apps.doctor.views.prescription_create) so Reception has a ready-made
    # invoice to collect payment for — no separate manual billing step.
    invoice = models.OneToOneField(
        'billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_order'
    )
    # Sample can only be marked collected once payment has cleared — see
    # `is_payment_cleared` / `can_collect_sample` below. Results can only
    # be entered once the sample has actually been collected.
    sample_collected = models.BooleanField(default=False)
    sample_collected_at = models.DateTimeField(null=True, blank=True)
    sample_collected_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='samples_collected'
    )

    def save(self, *args, **kwargs):
        if not self.verification_hash:
            self.verification_hash = uuid.uuid4().hex[:16]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"LAB-{self.voucher_code} — {self.patient.full_name}"

    @property
    def is_payment_cleared(self) -> bool:
        """No invoice at all (walk-in lab order, not doctor-ordered) counts
        as cleared — payment gating only applies to doctor-ordered tests
        that generated a real pending invoice."""
        if not self.invoice_id:
            return True
        return self.invoice.status == 'paid'

    @property
    def can_collect_sample(self) -> bool:
        return self.is_payment_cleared and not self.sample_collected

    @property
    def can_enter_results(self) -> bool:
        return self.sample_collected


class LabResult(TenantBaseModel):
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='results')
    test = models.ForeignKey(LabTestCatalog, on_delete=models.CASCADE)
    result_value = models.CharField(max_length=255)
    remarks = models.TextField(blank=True)
    is_abnormal = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=[('manual', 'Manual Entry'), ('analyzer', 'Analyzer Machine')], default='manual')

    def __str__(self):
        return f"{self.test.test_name}: {self.result_value}"
