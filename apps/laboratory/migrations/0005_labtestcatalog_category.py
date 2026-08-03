from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratory', '0004_sample_collection'),
    ]

    operations = [
        migrations.AddField(
            model_name='labtestcatalog',
            name='category',
            field=models.CharField(
                choices=[
                    ('clinical_chemistry', 'Clinical Chemistry'),
                    ('haematology', 'Haematology'),
                    ('microbiology', 'Microbiology'),
                    ('serology', 'Serology / Immunology'),
                    ('radiology', 'Radiology'),
                    ('cardiology', 'Cardiology'),
                    ('other', 'Other'),
                ],
                default='clinical_chemistry', max_length=30,
            ),
        ),
    ]
