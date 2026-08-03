from django.urls import path
from .views import home_redirect, tenant_initialize_api

app_name = 'core'

urlpatterns = [
    path('', home_redirect, name='home'),
]

# Public API (no app_name namespace needed, mounted separately in config/urls.py)
api_urlpatterns = [
    path('v1/tenant/initialize', tenant_initialize_api, name='tenant_initialize'),
]
