import uuid
from django.db import migrations, models


def populate_public_ids(apps, schema_editor):
    """Assign a fresh, unique UUID to every existing Clinic row.

    (AddField with unique=True + a callable default computes ONE default
    value for the whole ALTER TABLE on SQLite, which then collides across
    every existing row. Splitting into add-nullable -> populate -> make-
    unique avoids that entirely.)
    """
    Clinic = apps.get_model('core', 'Clinic')
    for clinic in Clinic.objects.all():
        clinic.public_id = uuid.uuid4()
        clinic.save(update_fields=['public_id'])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_clinic_is_assets_enabled'),
    ]

    operations = [
        # Step 1: add the column, nullable, no uniqueness constraint yet.
        migrations.AddField(
            model_name='clinic',
            name='public_id',
            field=models.UUIDField(null=True, editable=False, db_index=True),
        ),
        # Step 2: give every existing row its own unique UUID.
        migrations.RunPython(populate_public_ids, reverse_noop),
        # Step 3: now safe to enforce NOT NULL + UNIQUE.
        migrations.AlterField(
            model_name='clinic',
            name='public_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
