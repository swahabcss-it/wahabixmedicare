from django.conf import settings
from django.utils.deprecation import MiddlewareMixin


class SubdomainTenantMiddleware(MiddlewareMixin):
    """
    Blueprint requirement: dynamic subdomain routing (e.g. chughtai.cliniq.com).

    Resolves the clinic from the request's subdomain and stashes it on
    request.subdomain_clinic + request.is_subdomain_request. This runs BEFORE
    TenantMiddleware and never overrides authenticated staff/session-based
    tenant resolution — it only supplies branding (logo/colors) for the
    public-facing login page and white-labeled URLs. Actual data access is
    still governed by TenantMiddleware + role_required, so a bad/missing
    subdomain can never grant clinic data access on its own.
    """

    def process_request(self, request):
        request.subdomain_clinic = None
        request.is_subdomain_request = False

        base_domain = getattr(settings, 'BASE_DOMAIN', '')
        if not base_domain:
            return

        host = request.get_host().split(':')[0].lower()
        if not host.endswith(base_domain) or host == base_domain or host == f'www.{base_domain}':
            return

        subdomain = host[: -(len(base_domain) + 1)]
        if not subdomain or subdomain in ('api', 'admin', 'www'):
            return

        try:
            from apps.core.models import Clinic
            clinic = Clinic.objects.get(slug=subdomain, is_active=True)
            request.subdomain_clinic = clinic
            request.is_subdomain_request = True
        except Clinic.DoesNotExist:
            pass


class TenantMiddleware(MiddlewareMixin):
    """
    Injects request.clinic, request.staff_role, and request.is_sa_viewing
    on every request.

    ┌─────────────────────────────────────────────────────────────────┐
    │  Super Admin:                                                   │
    │    · Normally:  clinic=None, staff_role=None                    │
    │    · After selecting a clinic via /superadmin/clinics/<pk>/     │
    │      enter/: session['active_clinic_id'] is set, middleware     │
    │      loads that clinic and sets request.clinic so all module    │
    │      views return data for that tenant.                         │
    │    · request.is_sa_viewing = True signals templates to show     │
    │      the "Viewing as SuperAdmin" banner + Exit button.          │
    │                                                                 │
    │  Clinic Admin:                                                  │
    │    · clinic = their clinic (same as any staff)                  │
    │    · staff_role = 'clinic_admin'                                │
    │    · request.is_sa_viewing = False                              │
    │    · The role_required decorator grants clinic_admin access to  │
    │      all operational views within their clinic.                 │
    │                                                                 │
    │  Operational Staff:                                             │
    │    · clinic = their clinic                                      │
    │    · staff_role = their exact role                              │
    │    · Strict single-module access enforced by role_required.     │
    └─────────────────────────────────────────────────────────────────┘
    """
    EXEMPT_PATHS = [
        '/auth/', '/django-admin/', '/static/', '/media/',
    ]

    def process_request(self, request):
        request.clinic        = None
        request.staff_role    = None
        request.all_roles     = []
        request.is_sa_viewing = False   # True when superuser is viewing a specific clinic

        if not request.user.is_authenticated:
            return

        path = request.path_info

        # ── SUPER ADMIN ────────────────────────────────────────────────────────
        if request.user.is_superuser:
            # If a clinic has been selected for inspection, load it
            active_id = request.session.get('active_clinic_id')
            if active_id:
                try:
                    from apps.core.models import Clinic
                    clinic = Clinic.objects.get(pk=active_id, is_active=True)
                    request.clinic        = clinic
                    request.staff_role    = 'superadmin'   # special sentinel
                    request.is_sa_viewing = True
                except Exception:
                    # Clinic was deleted / deactivated — clear session
                    request.session.pop('active_clinic_id', None)
            return

        # ── EXEMPT PATHS (staff) ───────────────────────────────────────────────
        # Still populate clinic/role so base template works on superadmin/
        # home/ etc. even when path is exempt.
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            self._load_staff_profile(request)
            return

        # ── CLINIC STAFF ───────────────────────────────────────────────────────
        if not self._load_staff_profile(request):
            return

        # Suspension guard
        if request.clinic and request.clinic.is_suspended:
            from django.http import HttpResponse
            return HttpResponse(
                "<h2 style='font-family:sans-serif;color:#ef4444;"
                "text-align:center;margin-top:100px'>"
                "⛔ This clinic account has been suspended.<br>"
                "<small style='color:#666'>Contact Wahabix Medicare Support</small></h2>",
                status=403,
            )

    def _load_staff_profile(self, request) -> bool:
        try:
            profile = request.user.staff_profile
            request.clinic       = profile.clinic
            request.staff_role   = profile.role
            request.all_roles    = profile.get_all_roles()
            request.staff_profile_obj = profile
            return True
        except Exception:
            return False
