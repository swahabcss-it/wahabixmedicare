from django.urls import path
from . import views

app_name = 'clinic_admin'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('profile/', views.clinic_profile, name='clinic_profile'),
]
