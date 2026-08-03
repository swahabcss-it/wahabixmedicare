from django.urls import path
from . import views
app_name = 'billing'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/new/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('ledger/', views.ledger_report, name='ledger_report'),
    path('ledger/pdf/', views.ledger_pdf, name='ledger_pdf'),
    path('panels/', views.panel_list, name='panel_list'),
    path('claims/', views.claim_list, name='claim_list'),
    path('claims/batch-approve/', views.claim_batch_approve, name='claim_batch_approve'),
]
