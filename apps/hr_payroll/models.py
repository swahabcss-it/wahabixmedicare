from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TenantBaseModel


class Employee(TenantBaseModel):
    DEPT = [('lab','Laboratory'),('pharmacy','Pharmacy'),('reception','Reception'),('doctor','Doctor Room'),('admin','Administration'),('hr','HR & Accounts')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    department = models.CharField(max_length=30, choices=DEPT)
    designation = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    cnic = models.CharField(max_length=15)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    join_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name()} [{self.employee_id}]"


class PayrollSlip(TenantBaseModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    paid_on = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ['employee', 'month', 'year']

    def __str__(self):
        return f"{self.employee} — {self.month}/{self.year}"
