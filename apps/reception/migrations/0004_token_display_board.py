from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reception', '0003_patient_portal_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='token',
            name='called_at',
            field=models.DateTimeField(blank=True, null=True,
                                        help_text='When the doctor called this token in — drives the waiting-room display board'),
        ),
        migrations.AlterField(
            model_name='token',
            name='status',
            field=models.CharField(choices=[
                ('waiting', 'Waiting'), ('with_doctor', 'With Doctor'),
                ('sent_to_lab', 'Sent to Lab (Pre-Consultation)'),
                ('done', 'Done'), ('cancelled', 'Cancelled'),
            ], default='waiting', max_length=20),
        ),
    ]
