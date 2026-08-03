from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_clinic_public_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('theme', models.CharField(choices=[('dark', 'Dark'), ('light', 'Light'), ('ocean', 'Ocean'), ('emerald', 'Emerald'), ('rose', 'Rose'), ('sepia', 'Sepia'), ('contrast', 'High Contrast'), ('slate', 'Slate')], default='dark', max_length=20)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
