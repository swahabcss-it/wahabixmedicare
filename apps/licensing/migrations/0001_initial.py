# Generated manually (network-restricted sandbox)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0002_clinic_is_assets_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_type', models.CharField(choices=[('grace_period_started', 'Grace Period Started'), ('expired', 'Subscription Expired'), ('renewed', 'Subscription Renewed'), ('reminder_sent', 'Renewal Reminder Sent')], max_length=30)),
                ('plan_expires_at_event', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('clinic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='licensing_subscriptionevent_set', to='core.clinic')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='licensing_subscriptionevent_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
    ]
