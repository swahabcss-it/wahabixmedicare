from django.urls import path
from . import views
app_name = 'reception'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/new/', views.patient_create, name='patient_create'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/portal-access/', views.generate_portal_access, name='generate_portal_access'),
    path('tokens/', views.token_list, name='token_list'),
    path('tokens/new/', views.token_create, name='token_create'),
    path('tokens/<int:pk>/print/', views.token_print, name='token_print'),
    path('lab-payments/', views.pending_lab_payments, name='pending_lab_payments'),
    path('lab-payments/<int:invoice_pk>/collect/', views.collect_lab_payment, name='collect_lab_payment'),
    path('ajax/patient-search/', views.patient_search_ajax, name='patient_search_ajax'),
]
