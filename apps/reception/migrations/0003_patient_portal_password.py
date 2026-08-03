from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reception', '0002_token_invoice'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='portal_password_hash',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
