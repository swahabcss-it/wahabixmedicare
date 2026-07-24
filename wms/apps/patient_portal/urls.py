from django.urls import path
from . import views

app_name = 'patient_portal'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('prescriptions/<int:pk>/', views.view_prescription, name='view_prescription'),
    path('lab-reports/<int:pk>/', views.view_lab_report, name='view_lab_report'),
    path('invoices/<int:pk>/', views.view_invoice, name='view_invoice'),
]
