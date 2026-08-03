from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from apps.core.models import Clinic, StaffProfile


class Command(BaseCommand):
    help = (
        "Seeds demo clinics and one staff account per role (including the "
        "Super Admin and Clinic Admin) so the system can be explored "
        "immediately on a fresh database. Safe to re-run — existing "
        "users/clinics are left untouched."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--password', default='Demo@12345',
            help='Password to set for every newly created demo account (default: Demo@12345)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password']

        superuser, created = User.objects.get_or_create(
            username='wahabix',
            defaults=dict(first_name='Wahabix', last_name='Admin', is_superuser=True, is_staff=True),
        )
        if created:
            superuser.set_password(password)
            superuser.save()
            self.stdout.write(self.style.SUCCESS(f'Created Super Admin "wahabix" / {password}'))
        else:
            self.stdout.write('Super Admin "wahabix" already exists, skipped.')

        clinic, _ = Clinic.objects.get_or_create(
            slug='medicare-plus-demo',
            defaults=dict(
                name='Medicare Plus Demo Clinic',
                phone='+92 300 0000000',
                address='Demo Street, Lahore, Pakistan',
                plan='professional',
            ),
        )

        demo_staff = [
            ('admin_demo', 'Clinic', 'Admin', 'clinic_admin'),
            ('doctor_demo', 'Demo', 'Doctor', 'doctor'),
            ('lab_demo', 'Demo', 'LabSupervisor', 'lab_supervisor'),
            ('reception_demo', 'Demo', 'Receptionist', 'receptionist'),
            ('pharmacy_demo', 'Demo', 'Pharmacist', 'pharmacist'),
            ('hr_demo', 'Demo', 'HRManager', 'hr_manager'),
            ('accounts_demo', 'Demo', 'Accountant', 'accountant'),
        ]

        for username, first, last, role in demo_staff:
            user, created = User.objects.get_or_create(
                username=username, defaults=dict(first_name=first, last_name=last),
            )
            if created:
                user.set_password(password)
                user.save()
                StaffProfile.objects.create(clinic=clinic, user=user, role=role, phone='+92 300 0000000')
                self.stdout.write(self.style.SUCCESS(f'Created {role} "{username}" / {password}'))
            else:
                self.stdout.write(f'User "{username}" already exists, skipped.')

        # ── Lab Test Catalog ────────────────────────────────────────────────
        from apps.laboratory.models import LabTestCatalog
        lab_tests = [
            ('Complete Blood Count (CBC)', 'CBC',      600,  'See attached ranges per parameter', '',      'Blood', 6,  'haematology'),
            ('Blood Sugar Random (RBS)',   'RBS',      200,  '70–140 mg/dL',                      'mg/dL', 'Blood', 2,  'clinical_chemistry'),
            ('Blood Sugar Fasting (FBS)',  'FBS',      250,  '70–110 mg/dL',                      'mg/dL', 'Blood', 6,  'clinical_chemistry'),
            ('HbA1c',                      'HBA1C',    1800, '4–5.6 % (Normal)',                  '%',     'Blood', 24, 'clinical_chemistry'),
            ('Liver Function Test (LFT)',  'LFT',      1500, 'ALT 7–56, AST 10–40 U/L',           'U/L',   'Blood', 12, 'clinical_chemistry'),
            ('Renal Function Test (RFT)',  'RFT',      1200, 'Urea 15–40, Creat 0.6–1.2',         'mg/dL', 'Blood', 12, 'clinical_chemistry'),
            ('Lipid Profile',              'LIPID',    2000, 'Total Chol < 200 mg/dL',            'mg/dL', 'Blood', 12, 'clinical_chemistry'),
            ('Urine Routine Examination',  'URE',      400,  'No pus cells / no protein',         '',      'Urine', 4,  'microbiology'),
            ('Widal Test (Typhoid)',       'WIDAL',    500,  'Titre < 1:80',                      '',      'Blood', 6,  'serology'),
            ('Dengue NS1 Antigen',         'DENV-NS1', 1500, 'Negative',                          '',      'Blood', 6,  'serology'),
            ('Malaria Parasite (MP)',      'MP',       450,  'Negative',                          '',      'Blood', 2,  'microbiology'),
            ('Thyroid Profile (TSH/T3/T4)','TFT',      2200, 'TSH 0.4–4.0 mIU/L',                 'mIU/L', 'Blood', 24, 'clinical_chemistry'),
            ('Hepatitis B Surface Ag',     'HBSAG',    900,  'Non-Reactive',                      '',      'Blood', 12, 'serology'),
            ('Hepatitis C Antibody',       'ANTI-HCV', 900,  'Non-Reactive',                      '',      'Blood', 12, 'serology'),
            ('Pregnancy Test (Urine)',     'UPT',      300,  'Negative',                          '',      'Urine', 1,  'clinical_chemistry'),
            ('X-Ray Chest (PA View)',      'XRAY-CH',  1200, 'Radiologist opinion',               '',      'N/A',   4,  'radiology'),
            ('ECG',                        'ECG',      800,  'Normal Sinus Rhythm',               '',      'N/A',   1,  'cardiology'),
            ('Stool Routine Examination',  'SRE',      350,  'No ova / cyst / blood',             '',      'Stool', 6,  'microbiology'),
            ('Serum Electrolytes',         'ELECT',    1100, 'Na 135–145, K 3.5–5.1 mmol/L',      'mmol/L','Blood', 8,  'clinical_chemistry'),
            ('Vitamin D (25-OH)',          'VITD',     3500, '30–100 ng/mL (Sufficient)',         'ng/mL', 'Blood', 48, 'clinical_chemistry'),
        ]
        for name, code, rate, ref, unit, sample, hrs, category in lab_tests:
            LabTestCatalog.objects.get_or_create(
                clinic=clinic, test_code=code,
                defaults=dict(test_name=name, rate=rate, reference_range=ref,
                              unit=unit, sample_type=sample, turnaround_hours=hrs,
                              category=category, created_by=superuser),
            )
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(lab_tests)} lab tests.'))

        # ── Pharmacy Medicines + Stock Batches ──────────────────────────────
        from apps.pharmacy.models import Medicine, MedicineBatch
        from datetime import timedelta
        today = timezone.now().date()
        medicines = [
            ('Panadol',        'Paracetamol',        'GSK',          'tablet',    5,    8,    500),
            ('Brufen',         'Ibuprofen',           'Abbott',       'tablet',    8,    14,   300),
            ('Augmentin 625',  'Amoxicillin+Clav',    'GSK',          'tablet',    35,   55,   200),
            ('Flagyl',         'Metronidazole',       'Sanofi',       'tablet',    6,    12,   250),
            ('Amoxil',         'Amoxicillin',         'GSK',          'capsule',   10,   18,   300),
            ('Ponstan',        'Mefenamic Acid',      'Pfizer',       'tablet',    9,    16,   250),
            ('Disprin',        'Aspirin',             'Reckitt',      'tablet',    3,    6,    400),
            ('Calpol Syrup',   'Paracetamol',         'GSK',          'syrup',     120,  180,  80),
            ('Risek',          'Omeprazole',          'Getz Pharma',  'capsule',   12,   22,   250),
            ('Nexum',          'Esomeprazole',        'Getz Pharma',  'tablet',    18,   30,   200),
            ('Telfast',        'Fexofenadine',        'Sanofi',       'tablet',    22,   38,   150),
            ('Avil',           'Pheniramine',         'Sanofi',       'tablet',    4,    9,    300),
            ('Ventolin Inhaler','Salbutamol',         'GSK',          'other',     280,  420,  60),
            ('Wilgesic',       'Paracetamol+Tramadol','Wilshire',     'tablet',    15,   26,   200),
            ('D-Cal',          'Calcium+Vit D3',      'Wilshire',     'tablet',    10,   18,   300),
            ('Coledol Inj',    'Vitamin B Complex',   'Wilshire',     'injection', 45,   80,   100),
            ('Insulin Mixtard','Human Insulin',       'Novo Nordisk', 'injection', 350,  520,  50),
            ('Glucophage',     'Metformin',           'Merck',        'tablet',    7,    13,   300),
            ('Amlodac',        'Amlodipine',          'Zydus',        'tablet',    6,    11,   250),
            ('Concor 5',       'Bisoprolol',          'Merck',        'tablet',    14,   24,   200),
            ('Motilium',       'Domperidone',         'Janssen',      'tablet',    9,    16,   300),
            ('Azomax',         'Azithromycin',        'Getz Pharma',  'tablet',    45,   70,   200),
            ('Panadol CF',     'Paracetamol+Phenylephrine','GSK',     'tablet',    6,    11,   300),
            ('Arinac Forte',   'Ibuprofen+Pseudoephedrine','Abbott',  'tablet',    10,   18,   250),
            ('Rigix',          'Rabeprazole',         'Getz Pharma',  'tablet',    14,   24,   200),
            ('Zinnat',         'Cefuroxime',          'GSK',          'tablet',    55,   85,   150),
            ('Sinarest',       'Cetirizine+Paracetamol','Centaur',    'tablet',    7,    13,   250),
        ]
        for name, generic, brand, unit, pprice, sprice, stock in medicines:
            med, _ = Medicine.objects.get_or_create(
                clinic=clinic, name=name,
                defaults=dict(
                    generic_name=generic, brand=brand, unit=unit,
                    purchase_price=pprice, sale_price=sprice,
                    stock_quantity=stock, low_stock_alert=max(10, stock // 10),
                    expiry_date=today + timedelta(days=540),
                    created_by=superuser,
                ),
            )
            MedicineBatch.objects.get_or_create(
                clinic=clinic, medicine=med, batch_number=f'B-{med.pk:04d}-1',
                defaults=dict(quantity=stock, purchase_price=pprice,
                              expiry_date=today + timedelta(days=540), created_by=superuser),
            )
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(medicines)} medicines with stock batches.'))

        from apps.assets.models import AssetCategory, Asset
        from datetime import date
        cat, _ = AssetCategory.objects.get_or_create(
            clinic=clinic, name='Clinical Machines', defaults={'default_useful_life_years': 8}
        )
        Asset.objects.get_or_create(
            clinic=clinic, asset_tag='AST-0001',
            defaults=dict(
                category=cat, name='Digital X-Ray Machine', location='Radiology Room',
                purchase_date=date(2023, 1, 15), purchase_cost=1500000, salvage_value=100000,
                useful_life_years=8, vendor='MediTech Imports',
            ),
        )

        self.stdout.write(self.style.SUCCESS('\nDemo data ready. Log in at /auth/login/ with any of the usernames above.'))
