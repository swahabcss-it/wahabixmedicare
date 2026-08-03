import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reception', '0001_initial'),
        ('billing', '0003_invoice_is_ledgered_insurancepanel_insuranceclaim_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='token',
            name='invoice',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='reception_token', to='billing.invoice',
            ),
        ),
    ]
