from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TenantBaseModel
from apps.reception.models import Patient


class DoctorProfile(TenantBaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=255)
    qualification = models.CharField(max_length=255)
    pmdc_number = models.CharField(max_length=50, blank=True, verbose_name='PMDC No.')
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} — {self.specialization}"


class TreatmentTemplate(TenantBaseModel):
    """
    MANUAL FAIL-SAFE — 1-Click Prescription Sets.
    Doctor's most-used treatment protocols (e.g. "Typhoid Plan", "Cold & Flu").
    One click auto-fills ICD-11 code, diagnosis, chief complaint, medicines
    and lab tests — no typing, no mic required.
    """
    name = models.CharField(max_length=120, help_text='e.g. Typhoid Plan, Cold & Flu, Hypertension')
    icon = models.CharField(max_length=10, default='⭐', help_text='Emoji shown on the quick-button')
    icd11_code = models.CharField(max_length=20, blank=True, verbose_name='ICD-11 Code')
    diagnosis_text = models.CharField(max_length=255, blank=True)
    chief_complaint_text = models.CharField(max_length=255, blank=True)
    medicines_json = models.JSONField(default=list, blank=True)
    lab_tests = models.ManyToManyField('laboratory.LabTestCatalog', blank=True, related_name='templates')
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-usage_count', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class Prescription(TenantBaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='prescriptions')
    token = models.ForeignKey('reception.Token', on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
    template_used = models.ForeignKey(TreatmentTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    symptoms = models.TextField()
    diagnosis = models.TextField()
    icd11_code = models.CharField(max_length=20, blank=True, verbose_name='ICD-11 Code')
    notes = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    visit_date = models.DateTimeField(auto_now_add=True)
    lab_order = models.ForeignKey('laboratory.LabOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_prescription')
    dispatched_to_pharmacy = models.BooleanField(default=False)
    dispatched_to_lab = models.BooleanField(default=False)

    def __str__(self):
        return f"RX-{self.pk:04d} — {self.patient.full_name}"


class PrescriptionMedicine(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medicines')
    medicine_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)

    def __str__(self):
        return f"{self.medicine_name} — {self.dosage}"
