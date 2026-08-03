from django.db import models
from apps.core.models import TenantBaseModel


class Medicine(TenantBaseModel):
    UNIT = [('tablet','Tablet'),('capsule','Capsule'),('syrup','Syrup'),('injection','Injection'),('cream','Cream'),('drops','Drops'),('other','Other')]
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=64, blank=True, db_index=True, help_text='Scan with laser gun or type manually')
    unit = models.CharField(max_length=20, choices=UNIT, default='tablet')
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0, help_text='Legacy flat stock — used only if no batches exist')
    low_stock_alert = models.PositiveIntegerField(default=10)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} [{self.brand}] — Rs.{self.sale_price}"

    @property
    def total_stock(self):
        """FEFO-aware total: sum of active batch quantities, else legacy flat field."""
        agg = self.batches.filter(quantity__gt=0).aggregate(total=models.Sum('quantity'))
        return agg['total'] if agg['total'] is not None and self.batches.exists() else self.stock_quantity

    @property
    def is_low_stock(self):
        return self.total_stock <= self.low_stock_alert

    @property
    def is_expired(self):
        from django.utils import timezone
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def nearest_expiry(self):
        b = self.batches.filter(quantity__gt=0).order_by('expiry_date').first()
        return b.expiry_date if b else self.expiry_date

    def deduct_fefo(self, qty):
        """
        🟢 AUTO MODE — FEFO Inventory Allocation.
        Deducts from the batch expiring soonest first (First-Expiry-First-Out)
        so an expired batch is never dispensed. Falls back to the flat
        stock_quantity field for clinics that haven't migrated to batches yet.
        """
        remaining = qty
        batches = list(self.batches.filter(quantity__gt=0).order_by('expiry_date'))
        if not batches:
            if self.stock_quantity < qty:
                raise ValueError(f'Insufficient stock for {self.name}: only {self.stock_quantity} left.')
            self.stock_quantity -= qty
            self.save(update_fields=['stock_quantity'])
            return
        total_available = sum(b.quantity for b in batches)
        if total_available < qty:
            raise ValueError(f'Insufficient stock for {self.name}: only {total_available} left across all batches.')
        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.quantity, remaining)
            batch.quantity -= take
            batch.save(update_fields=['quantity'])
            remaining -= take


class MedicineBatch(TenantBaseModel):
    """Individual purchase batch — enables FEFO (First-Expiry-First-Out) allocation."""
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    expiry_date = models.DateField()

    class Meta:
        ordering = ['expiry_date']

    def __str__(self):
        return f"{self.medicine.name} — Batch {self.batch_number} (exp {self.expiry_date}) x{self.quantity}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()


class PharmacySale(TenantBaseModel):
    STATUS = [('pending','Pending'),('paid','Paid'),('cancelled','Cancelled')]
    patient_name = models.CharField(max_length=255, blank=True)
    invoice_number = models.CharField(max_length=30, unique=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default='paid')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"INV-{self.invoice_number}"


class PharmacySaleItem(models.Model):
    sale = models.ForeignKey(PharmacySale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)
