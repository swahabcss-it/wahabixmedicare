# Generated manually (network-restricted sandbox)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0002_clinic_is_assets_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('default_useful_life_years', models.PositiveIntegerField(default=5, help_text='Used to prefill new assets in this category')),
                ('clinic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets_assetcategory_set', to='core.clinic')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets_assetcategory_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Asset Categories',
                'ordering': ['name'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Asset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('asset_tag', models.CharField(help_text='Barcode / asset tag ID', max_length=40, unique=True)),
                ('serial_number', models.CharField(blank=True, max_length=100)),
                ('location', models.CharField(blank=True, help_text='Room / branch / department', max_length=150)),
                ('purchase_date', models.DateField()),
                ('purchase_cost', models.DecimalField(decimal_places=2, max_digits=12)),
                ('salvage_value', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('useful_life_years', models.PositiveIntegerField(default=5)),
                ('depreciation_method', models.CharField(choices=[('straight_line', 'Straight-Line'), ('none', 'Not Depreciated')], default='straight_line', max_length=20)),
                ('vendor', models.CharField(blank=True, max_length=255)),
                ('warranty_expires', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('in_use', 'In Use'), ('under_maintenance', 'Under Maintenance'), ('retired', 'Retired'), ('disposed', 'Disposed')], default='in_use', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='assets', to='assets.assetcategory')),
                ('clinic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets_asset_set', to='core.clinic')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets_asset_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-purchase_date'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AssetServiceLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('service_type', models.CharField(choices=[('routine', 'Routine Maintenance'), ('repair', 'Repair'), ('inspection', 'Inspection / Calibration'), ('emergency', 'Emergency Service')], default='routine', max_length=20)),
                ('service_date', models.DateField()),
                ('performed_by', models.CharField(blank=True, help_text='Technician / vendor name', max_length=255)),
                ('cost', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('description', models.TextField(blank=True)),
                ('next_service_due', models.DateField(blank=True, null=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_logs', to='assets.asset')),
                ('clinic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets_assetservicelog_set', to='core.clinic')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assets_assetservicelog_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-service_date'],
                'abstract': False,
            },
        ),
    ]
