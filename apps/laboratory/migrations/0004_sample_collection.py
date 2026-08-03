import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratory', '0003_laborder_invoice'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='laborder',
            name='sample_collected',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='laborder',
            name='sample_collected_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='laborder',
            name='sample_collected_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='samples_collected', to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
