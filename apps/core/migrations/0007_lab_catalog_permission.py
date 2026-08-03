from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_submodule_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffprofile',
            name='can_edit_lab_catalog',
            field=models.BooleanField(
                default=False,
                help_text="Lets this person add/edit/remove tests in the Lab Test Catalogue (prices, "
                          "reference ranges, turnaround times). Separate from result-deletion rights on "
                          "purpose — someone trusted to key in results isn't automatically trusted to "
                          "change what a test costs or its clinical reference range.",
            ),
        ),
    ]
