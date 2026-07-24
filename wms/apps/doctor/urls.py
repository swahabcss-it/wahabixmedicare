from django.urls import path
from . import views
app_name = 'doctor'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('queue/', views.patient_queue, name='queue'),
    path('queue/<int:token_pk>/call/', views.call_patient, name='call_patient'),
    path('queue/<int:token_pk>/prescribe/', views.prescription_create, name='prescription_create'),
    path('prescriptions/', views.prescription_list, name='prescription_list'),
    path('prescriptions/<int:pk>/', views.prescription_detail, name='prescription_detail'),
    path('prescriptions/<int:pk>/edit/', views.prescription_edit, name='prescription_edit'),
    path('prescriptions/<int:pk>/print/', views.prescription_print, name='prescription_print'),
    path('prescriptions/<int:pk>/pdf/', views.prescription_pdf, name='prescription_pdf'),
    path('templates/', views.template_list, name='template_list'),
    path('templates/new/', views.template_create, name='template_create'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:pk>/apply/', views.template_apply_ajax, name='template_apply_ajax'),
]
