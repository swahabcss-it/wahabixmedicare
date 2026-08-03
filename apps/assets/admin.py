from django.contrib import admin
from .models import AssetCategory, Asset, AssetServiceLog


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'clinic', 'default_useful_life_years')
    list_filter = ('clinic',)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'asset_tag', 'clinic', 'category', 'status', 'purchase_cost', 'current_book_value')
    list_filter = ('clinic', 'status', 'category')
    search_fields = ('name', 'asset_tag', 'serial_number')


@admin.register(AssetServiceLog)
class AssetServiceLogAdmin(admin.ModelAdmin):
    list_display = ('asset', 'service_type', 'service_date', 'cost', 'next_service_due')
    list_filter = ('clinic', 'service_type')
