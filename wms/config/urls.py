from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve as static_serve
from django.shortcuts import redirect
from apps.core.urls import api_urlpatterns

urlpatterns = [
    path('', lambda r: redirect('core:home') if r.user.is_authenticated else redirect('auth:login')),
    path('django-admin/', admin.site.urls),
    path('auth/', include('apps.core.urls_auth', namespace='auth')),
    path('home/', include('apps.core.urls', namespace='core')),
    path('superadmin/', include('apps.superadmin_panel.urls', namespace='superadmin')),
    path('clinic-admin/', include('apps.clinic_admin.urls', namespace='clinic_admin')),
    path('reception/', include('apps.reception.urls', namespace='reception')),
    path('lab/', include('apps.laboratory.urls', namespace='laboratory')),
    path('doctor/', include('apps.doctor.urls', namespace='doctor')),
    path('pharmacy/', include('apps.pharmacy.urls', namespace='pharmacy')),
    path('hr/', include('apps.hr_payroll.urls', namespace='hr_payroll')),
    path('billing/', include('apps.billing.urls', namespace='billing')),
    path('assets-module/', include('apps.assets.urls', namespace='assets')),
    path('patient-portal/', include('apps.patient_portal.urls', namespace='patient_portal')),
    path('api/', include((api_urlpatterns, 'core_api'))),
    # Serve uploaded media (clinic logos, etc.) unconditionally — NOT gated
    # by DEBUG. Django's usual `static()` helper from
    # django.conf.urls.static silently does nothing when DEBUG=False,
    # which is exactly why logos disappeared as soon as DEBUG got set to
    # False. This is a plain synchronous view, so it's not the fastest way
    # to serve files at real scale, but for this app's actual deployment
    # (a small clinic server) working reliably matters far more than that.
    re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
]
