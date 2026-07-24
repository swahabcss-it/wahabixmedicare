from django.db import models
from apps.core.models import TenantBaseModel
from apps.reception.models import Patient


class InsurancePanel(TenantBaseModel):
    """A panel/insurer the clinic has an agreement with (e.g. 'State Life', 'Jubilee')."""
    name = models.CharField(max_length=255)
    co_payment_percent = models.DecimalField(max_digits=5, decimal_places=2, default=20,
                                               help_text='% the PATIENT pays; the rest is billed to the insurer')
    contact_person = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.co_payment_percent}% co-pay)"


class Invoice(TenantBaseModel):
    STATUS = [('draft','Draft'),('paid','Paid'),('partial','Partial'),('cancelled','Cancelled')]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=30, unique=True)
    insurance_panel = models.ForeignKey(InsurancePanel, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='draft')
    notes = models.TextField(blank=True)
    is_ledgered = models.BooleanField(default=False, help_text='Guards against duplicate autonomous ledger entries')

    def __str__(self):
        return f"INV-{self.invoice_number} — {self.patient.full_name}"

    @property
    def balance_due(self):
        return self.total - self.amount_paid


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class InsuranceClaim(TenantBaseModel):
    """
    🟢 AUTO MODE — Insurance Claim Scrubbing.
    Auto-generated the moment a panel-patient's invoice is locked: splits
    co-payment vs insurer-share per the panel's agreed percentage.
    """
    STATUS = [('pending','Pending'),('submitted','Submitted'),('approved','Approved'),('rejected','Rejected')]
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='claim')
    panel = models.ForeignKey(InsurancePanel, on_delete=models.CASCADE, related_name='claims')
    patient_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    insurer_share = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    batch_ref = models.CharField(max_length=40, blank=True, help_text='Set when batch-submitted together')
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Claim #{self.pk} — {self.invoice.invoice_number} ({self.panel.name})"


class LedgerEntry(TenantBaseModel):
    """
    🟢 AUTO MODE — Autonomous General Ledger.
    Every cleared transaction (invoice payment, pharmacy sale) automatically
    routes a debit/credit pair here — no manual bookkeeping.
    """
    ACCOUNTS = [
        ('cash_vault', 'Central Operating Cash Vault'),
        ('consultation_revenue', 'Consultation Revenue'),
        ('pharmacy_revenue', 'Pharmacy Revenue'),
        ('lab_revenue', 'Laboratory Revenue'),
        ('insurance_receivable', 'Insurance Receivable'),
    ]
    ENTRY_TYPE = [('debit', 'Debit'), ('credit', 'Credit')]
    date = models.DateField()
    account = models.CharField(max_length=40, choices=ACCOUNTS)
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=60, help_text='e.g. INV-202607-0001, PH20260702-0004')
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date} · {self.get_account_display()} · {self.get_entry_type_display()} Rs.{self.amount}"
