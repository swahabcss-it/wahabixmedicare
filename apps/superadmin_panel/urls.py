from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('clinics/', views.clinic_list, name='clinic_list'),
    path('clinics/create/', views.clinic_create, name='clinic_create'),
    path('clinics/<int:pk>/', views.clinic_detail, name='clinic_detail'),
    path('clinics/<int:pk>/edit/', views.clinic_edit, name='clinic_edit'),
    path('clinics/<int:pk>/toggle-suspend/', views.clinic_toggle_suspend, name='clinic_toggle_suspend'),
    path('clinics/<int:pk>/enter/', views.clinic_enter, name='clinic_enter'),
    path('clinics/exit/', views.clinic_exit, name='clinic_exit'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    path('settings/', views.platform_settings, name='platform_settings'),
]
