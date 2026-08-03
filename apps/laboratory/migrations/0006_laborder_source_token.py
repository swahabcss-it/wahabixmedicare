import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratory', '0005_labtestcatalog_category'),
        ('reception', '0004_token_display_board'),
    ]

    operations = [
        migrations.AddField(
            model_name='laborder',
            name='source_token',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='lab_referrals', to='reception.token',
            ),
        ),
    ]
