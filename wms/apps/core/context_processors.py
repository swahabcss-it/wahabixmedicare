from django.conf import settings
from apps.core.models import PlatformSettings


def global_context(request):
    """
    Global template context.

    Nav visibility rules:
    ┌──────────────────┬────────────────────────────────────────────────┐
    │ Role             │ Nav shown                                      │
    ├──────────────────┼────────────────────────────────────────────────┤
    │ superuser        │ All modules of the currently-selected clinic   │
    │                  │ (or nothing operational if no clinic selected) │
    │ clinic_admin     │ Clinic-Admin panel + ALL enabled modules       │
    │ doctor           │ Doctor module only                             │
    │ lab_supervisor   │ Laboratory module only                         │
    │ receptionist     │ Reception module only                          │
    │ pharmacist       │ Pharmacy module only                           │
    │ hr_manager       │ HR & Payroll module only                       │
    │ accountant       │ Billing module only                            │
    └──────────────────┴────────────────────────────────────────────────┘
    """
    clinic         = getattr(request, 'clinic', None)
    role           = getattr(request, 'staff_role', None)
    all_roles      = getattr(request, 'all_roles', [role] if role else [])
    is_sa_viewing  = getattr(request, 'is_sa_viewing', False)
    is_sa          = getattr(request.user, 'is_superuser', False) if hasattr(request, 'user') else False
    is_ca          = role == 'clinic_admin'

    def _module_on(flag: str) -> bool:
        """Is this module enabled for the current clinic?"""
        return bool(clinic and getattr(clinic, flag, False))

    def _nav(flag: str, required_role: str) -> bool:
        """
        Should this module's nav section be visible?
        - Superuser: yes, if a clinic is selected and module is enabled.
        - Clinic admin: yes, if module is enabled for their clinic.
        - Operational staff: yes if their PRIMARY role matches, OR the
          required role is one of their granted extra (multi-module) roles.
        """
        if is_sa:
            return is_sa_viewing and _module_on(flag)
        if is_ca:
            return _module_on(flag)
        return _module_on(flag) and required_role in all_roles

    return {
        # App meta
        'IS_DEBUG':       settings.DEBUG,
        'SHOW_DEMO_LOGIN': settings.SHOW_DEMO_LOGIN,
        'PLATFORM_THEME': PlatformSettings.get().theme,
        'APP_NAME':       getattr(settings, 'APP_NAME',      'Wahabix Medicare Solution'),
        'APP_VERSION':    getattr(settings, 'APP_VERSION',    '2.2'),
        'APP_DEVELOPER':  getattr(settings, 'APP_DEVELOPER',  'WAHABIX'),
        'APP_YEAR':       getattr(settings, 'APP_YEAR',       '2026'),

        # Tenant context
        'current_clinic':    clinic,
        'staff_role':        role,
        'is_clinic_admin':   is_ca,
        'is_sa_viewing':     is_sa_viewing,  # True when superuser is inside a clinic

        # Module nav flags
        'nav_show_reception': _nav('is_reception_enabled', 'receptionist'),
        'nav_show_doctor':    _nav('is_doctor_enabled',    'doctor'),
        'nav_show_lab':       _nav('is_lab_enabled',       'lab_supervisor'),
        'nav_show_pharmacy':  _nav('is_pharmacy_enabled',  'pharmacist'),
        'nav_show_hr':        _nav('is_hr_enabled',        'hr_manager'),
        'nav_show_billing':   _nav('is_billing_enabled',   'accountant'),
        'nav_show_invoicing_access': (
            _module_on('is_billing_enabled') and (
                is_sa and is_sa_viewing or is_ca or
                getattr(getattr(request, 'staff_profile_obj', None), 'can_access_billing', False)
            ) and role != 'accountant'  # accountants already have full billing nav above
        ),
        'subscription_status':     getattr(request, 'subscription_status', None),
        'subscription_days_left':  getattr(request, 'subscription_days_left', None),
        'nav_show_assets':    (
            (is_sa and is_sa_viewing and _module_on('is_assets_enabled')) or
            (is_ca and _module_on('is_assets_enabled')) or
            (_module_on('is_assets_enabled') and role in ('accountant', 'hr_manager'))
        ),
    }
