import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratory', '0002_laborder_is_verified_laborder_verification_hash_and_more'),
        ('billing', '0003_invoice_is_ledgered_insurancepanel_insuranceclaim_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='laborder',
            name='invoice',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='lab_order', to='billing.invoice',
            ),
        ),
    ]
