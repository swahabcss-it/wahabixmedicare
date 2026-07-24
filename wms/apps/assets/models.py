from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TenantBaseModel


class AssetCategory(TenantBaseModel):
    """e.g. 'Clinical Machines', 'Furniture', 'IT Equipment'"""
    name = models.CharField(max_length=100)
    default_useful_life_years = models.PositiveIntegerField(
        default=5, help_text='Used to prefill new assets in this category'
    )

    class Meta:
        verbose_name_plural = 'Asset Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Asset(TenantBaseModel):
    """
    Heavy clinical machines, branch furniture, IT equipment, etc.
    Tracks straight-line depreciation and lifecycle status.
    """
    STATUS = [
        ('in_use', 'In Use'),
        ('under_maintenance', 'Under Maintenance'),
        ('retired', 'Retired'),
        ('disposed', 'Disposed'),
    ]
    DEPRECIATION_METHOD = [
        ('straight_line', 'Straight-Line'),
        ('none', 'Not Depreciated'),
    ]

    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, related_name='assets')
    name = models.CharField(max_length=255)
    asset_tag = models.CharField(max_length=40, unique=True, help_text='Barcode / asset tag ID')
    serial_number = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, blank=True, help_text='Room / branch / department')

    purchase_date = models.DateField()
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2)
    salvage_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    useful_life_years = models.PositiveIntegerField(default=5)
    depreciation_method = models.CharField(max_length=20, choices=DEPRECIATION_METHOD, default='straight_line')

    vendor = models.CharField(max_length=255, blank=True)
    warranty_expires = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='in_use')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-purchase_date']

    def __str__(self):
        return f"{self.name} ({self.asset_tag})"

    @property
    def age_years(self) -> Decimal:
        days = (timezone.now().date() - self.purchase_date).days
        return Decimal(days) / Decimal('365.25')

    @property
    def annual_depreciation(self) -> Decimal:
        if self.depreciation_method != 'straight_line' or self.useful_life_years <= 0:
            return Decimal('0.00')
        depreciable_base = self.purchase_cost - self.salvage_value
        return (depreciable_base / self.useful_life_years).quantize(Decimal('0.01'))

    @property
    def accumulated_depreciation(self) -> Decimal:
        if self.depreciation_method != 'straight_line':
            return Decimal('0.00')
        elapsed_full_years = min(int(self.age_years), self.useful_life_years)
        accumulated = self.annual_depreciation * elapsed_full_years
        max_depreciable = self.purchase_cost - self.salvage_value
        return min(accumulated, max_depreciable).quantize(Decimal('0.01'))

    @property
    def current_book_value(self) -> Decimal:
        return (self.purchase_cost - self.accumulated_depreciation).quantize(Decimal('0.01'))

    @property
    def is_fully_depreciated(self) -> bool:
        return self.accumulated_depreciation >= (self.purchase_cost - self.salvage_value)

    @property
    def warranty_active(self) -> bool:
        return bool(self.warranty_expires and self.warranty_expires >= timezone.now().date())


class AssetServiceLog(TenantBaseModel):
    """Monthly / ad-hoc maintenance & service history per asset."""
    SERVICE_TYPE = [
        ('routine', 'Routine Maintenance'),
        ('repair', 'Repair'),
        ('inspection', 'Inspection / Calibration'),
        ('emergency', 'Emergency Service'),
    ]
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='service_logs')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE, default='routine')
    service_date = models.DateField()
    performed_by = models.CharField(max_length=255, blank=True, help_text='Technician / vendor name')
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    next_service_due = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-service_date']

    def __str__(self):
        return f"{self.asset.name} — {self.get_service_type_display()} on {self.service_date}"

    @property
    def is_overdue(self) -> bool:
        return bool(self.next_service_due and self.next_service_due < timezone.now().date())
