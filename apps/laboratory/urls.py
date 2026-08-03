from django.urls import path
from . import views
app_name = 'laboratory'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('tests/', views.test_catalog, name='test_catalog'),
    path('tests/new/', views.test_create, name='test_create'),
    path('tests/<int:pk>/edit/', views.test_edit, name='test_edit'),
    path('tests/<int:pk>/delete/', views.test_soft_delete, name='test_delete'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/new/', views.order_create, name='order_create'),
    path('orders/<int:order_pk>/results/', views.result_entry, name='result_entry'),
    path('orders/<int:order_pk>/collect-sample/', views.mark_sample_collected, name='mark_sample_collected'),
    path('orders/<int:order_pk>/pdf/', views.result_pdf, name='result_pdf'),
    path('orders/<int:order_pk>/verify/', views.order_verify, name='order_verify'),
    path('orders/<int:pk>/delete/', views.order_soft_delete, name='order_soft_delete'),
    path('results/<int:pk>/delete/', views.result_soft_delete, name='result_soft_delete'),
    path('verify/<str:voucher_code>/<str:verification_hash>/', views.verify_report_public, name='verify_report_public'),
    path('webhook/analyzer/', views.analyzer_webhook, name='analyzer_webhook'),
]
