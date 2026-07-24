from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_platformsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffprofile',
            name='extra_roles',
            field=models.CharField(blank=True, max_length=200,
                                    help_text='Comma-separated additional roles this person can also access (multi-module access)'),
        ),
        migrations.AddField(
            model_name='staffprofile',
            name='can_access_billing',
            field=models.BooleanField(default=False,
                                       help_text="Lets this person view/create/print invoices (e.g. a receptionist or lab staffer "
                                                 "handling walk-in payments) without giving them full Accountant/ledger access. "
                                                 "Accountants always have full billing access regardless of this flag."),
        ),
        migrations.AlterField(
            model_name='staffprofile',
            name='role',
            field=models.CharField(choices=[
                ('clinic_admin', 'Clinic Admin'), ('doctor', 'Doctor'), ('lab_supervisor', 'Lab Supervisor'),
                ('pharmacist', 'Pharmacist'), ('receptionist', 'Receptionist'), ('hr_manager', 'HR Manager'),
                ('accountant', 'Accountant'),
            ], help_text='Primary role — decides their main dashboard/home screen', max_length=30),
        ),
    ]
