from django.contrib import admin
from .models import SubscriptionEvent


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    list_display = ('clinic', 'event_type', 'plan_expires_at_event', 'created_at')
    list_filter = ('event_type',)
    readonly_fields = ('created_at',)
