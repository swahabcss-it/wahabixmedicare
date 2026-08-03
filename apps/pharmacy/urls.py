from django.urls import path
from . import views
app_name = 'pharmacy'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('medicines/', views.medicine_list, name='medicine_list'),
    path('medicines/add/', views.medicine_create, name='medicine_create'),
    path('medicines/<int:pk>/edit/', views.medicine_edit, name='medicine_edit'),
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/new/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/pdf/', views.sale_pdf, name='sale_pdf'),
    path('pos/', views.pos, name='pos'),
    path('ajax/search/', views.medicine_search_ajax, name='medicine_search_ajax'),
    path('ajax/scan/', views.medicine_scan_ajax, name='medicine_scan_ajax'),
    path('ajax/fetch-rx/<int:token_pk>/', views.fetch_prescription_cart_ajax, name='fetch_prescription_cart_ajax'),
    path('medicines/<int:med_pk>/batches/', views.batch_list, name='batch_list'),
]
