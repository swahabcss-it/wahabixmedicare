from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('list/', views.asset_list, name='asset_list'),
    path('new/', views.asset_create, name='asset_create'),
    path('<int:pk>/', views.asset_detail, name='asset_detail'),
    path('<int:asset_pk>/service/new/', views.service_log_create, name='service_log_create'),
]
