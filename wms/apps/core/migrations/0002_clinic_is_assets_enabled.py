# Generated manually (network-restricted sandbox) — adds Clinic.is_assets_enabled

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinic',
            name='is_assets_enabled',
            field=models.BooleanField(default=True),
        ),
    ]
