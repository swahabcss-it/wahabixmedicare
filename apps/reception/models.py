from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from apps.core.models import TenantBaseModel
import secrets
import string


class Patient(TenantBaseModel):
    GENDER = [('M','Male'),('F','Female'),('O','Other')]
    BLOOD = [('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('O+','O+'),('O-','O-'),('AB+','AB+'),('AB-','AB-')]

    full_name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=1, choices=GENDER)
    phone = models.CharField(max_length=20)
    cnic = models.CharField(max_length=15, blank=True, verbose_name='CNIC')
    blood_group = models.CharField(max_length=4, choices=BLOOD, blank=True)
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    allergies = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # ── Patient Portal login ────────────────────────────────────────────
    # Username is the Patient ID (P-0004) — no separate field needed.
    # Password is a short auto-generated code (shown once to Reception at
    # registration time, exactly like the "Username / Password" slip in
    # the reference report), hashed the same way Django hashes staff
    # passwords — never stored or displayed in plain text after creation.
    portal_password_hash = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} (P-{self.pk:04d})"

    @property
    def patient_id(self):
        return f"P-{self.pk:04d}"

    def generate_portal_password(self) -> str:
        """Generates and stores a new portal password, returning the
        plain-text value ONCE so Reception can print/share it with the
        patient. Never call this and discard the return value — that
        password can't be recovered afterward, only reset."""
        alphabet = string.ascii_lowercase + string.digits
        plain = ''.join(secrets.choice(alphabet) for _ in range(6))
        self.portal_password_hash = make_password(plain)
        self.save(update_fields=['portal_password_hash'])
        return plain

    def check_portal_password(self, raw_password: str) -> bool:
        if not self.portal_password_hash:
            return False
        return check_password(raw_password, self.portal_password_hash)


class Token(TenantBaseModel):
    STATUS = [
        ('waiting','Waiting'),
        ('with_doctor','With Doctor'),
        ('sent_to_lab','Sent to Lab (Pre-Consultation)'),
        ('done','Done'),
        ('cancelled','Cancelled'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='tokens')
    token_number = models.PositiveIntegerField()
    doctor = models.ForeignKey('doctor.DoctorProfile', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='waiting')
    visit_date = models.DateField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True, help_text='When the doctor called this token in — drives the waiting-room display board')
    fee_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # The token doubles as the reception invoice/receipt — created
    # automatically the moment the fee is collected at the counter.
    invoice = models.OneToOneField(
        'billing.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='reception_token'
    )
    # Vitals
    blood_pressure = models.CharField(max_length=20, blank=True)
    temperature = models.CharField(max_length=10, blank=True)
    weight = models.CharField(max_length=10, blank=True)
    pulse = models.CharField(max_length=10, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['token_number']

    def __str__(self):
        return f"Token #{self.token_number} — {self.patient.full_name}"
