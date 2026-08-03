from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_staff_multirole_billing'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinic',
            name='submodule_map',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='staffprofile',
            name='enabled_submodules',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
