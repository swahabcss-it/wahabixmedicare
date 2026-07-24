from django.contrib import admin
from .models import Clinic, StaffProfile, AuditLog


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'plan', 'is_active', 'is_suspended', 'created_at']
    list_filter = ['plan', 'is_active', 'is_suspended']
    search_fields = ['name', 'slug', 'email']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'clinic', 'role', 'is_active']
    list_filter = ['role', 'clinic']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'clinic', 'ip_address']
    list_filter = ['clinic']
    readonly_fields = ['timestamp']
