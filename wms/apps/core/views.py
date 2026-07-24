from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages

ROLE_DASHBOARDS = {
    'clinic_admin':   ('clinic_admin:dashboard', None),
    'doctor':         ('doctor:dashboard',        'is_doctor_enabled'),
    'lab_supervisor': ('laboratory:dashboard',    'is_lab_enabled'),
    'receptionist':   ('reception:dashboard',     'is_reception_enabled'),
    'pharmacist':     ('pharmacy:dashboard',      'is_pharmacy_enabled'),
    'hr_manager':     ('hr_payroll:dashboard',    'is_hr_enabled'),
    'accountant':     ('billing:dashboard',       'is_billing_enabled'),
}


@login_required
def home_redirect(request):
    """
    Universal role-aware landing page.

    Super Admin (no clinic selected)  → /superadmin/dashboard/
    Super Admin (clinic selected)      → clinic home template (shows all modules)
    Clinic Admin                       → /clinic-admin/dashboard/
    Operational staff                  → their specific module dashboard
    """
    # ── SUPER ADMIN ───────────────────────────────────────────────────────────
    if request.user.is_superuser:
        if getattr(request, 'is_sa_viewing', False):
            # Superadmin is inside a clinic → show a landing with all modules
            return render(request, 'core/sa_clinic_home.html', {
                'clinic': request.clinic,
            })
        return redirect('superadmin:dashboard')

    # ── CLINIC STAFF ──────────────────────────────────────────────────────────
    staff_role = getattr(request, 'staff_role', None)
    clinic     = getattr(request, 'clinic', None)
    mapping    = ROLE_DASHBOARDS.get(staff_role)

    if mapping and clinic:
        url_name, flag = mapping
        if flag is None or getattr(clinic, flag, True):
            return redirect(url_name)
        messages.warning(
            request,
            f"The {staff_role.replace('_', ' ').title()} module isn't enabled "
            f"for {clinic.name}. Contact your clinic admin or Wahabix Support."
        )
        logout(request)
        return redirect('auth:login')

    logout(request)
    messages.error(
        request,
        'Your account is not linked to an active clinic role. '
        'Contact your administrator.'
    )
    return redirect('auth:login')


# ── Public Tenant-Initialization API (Blueprint §2: Dynamic Subdomains) ────
def tenant_initialize_api(request):
    """
    GET /api/v1/tenant/initialize?subdomain=chughtai

    Public, unauthenticated, read-only endpoint used by the frontend right
    after extracting the subdomain from window.location. Returns ONLY
    non-sensitive branding + subscription-status info needed to render the
    white-labeled login screen. Never exposes patient data, staff data, or
    anything requiring auth — that all still goes through TenantMiddleware
    and role_required after login.
    """
    from django.http import JsonResponse
    from apps.core.models import Clinic

    subdomain = request.GET.get('subdomain', '').strip().lower()
    if not subdomain:
        return JsonResponse({'error': 'subdomain parameter required'}, status=400)

    clinic = Clinic.objects.filter(slug=subdomain, is_active=True).first()
    if not clinic:
        return JsonResponse({'error': 'Unknown clinic subdomain'}, status=404)

    return JsonResponse({
        'clinic_id': str(clinic.public_id),
        'clinic_name': clinic.name,
        'slug': clinic.slug,
        'logo_url': clinic.logo.url if clinic.logo else None,
        'is_suspended': clinic.is_suspended,
        'plan': clinic.plan,
        'subscription_active': clinic.is_plan_active and not clinic.is_suspended,
        'enabled_modules': [m[0] for m in clinic.enabled_modules()],
    })
