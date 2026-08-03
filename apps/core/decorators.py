from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*allowed_roles, feature_flag=None, permission_flag=None):
    """
    Access-control decorator for clinic-level views.

    WHO GETS IN:
    ┌──────────────────────┬──────────────────────────────────────────────┐
    │ User type            │ Access                                       │
    ├──────────────────────┼──────────────────────────────────────────────┤
    │ is_superuser         │ Always passes. request.clinic comes from     │
    │                      │ session (set by clinic enter/exit views).    │
    │                      │ If no clinic selected, view still runs but   │
    │                      │ querysets return empty (no clinic filter).   │
    ├──────────────────────┼──────────────────────────────────────────────┤
    │ clinic_admin         │ Passes ALL operational role checks within    │
    │                      │ their clinic. They can use every module      │
    │                      │ the clinic has enabled. This is the intended │
    │                      │ "manager who oversees everything" role.      │
    ├──────────────────────┼──────────────────────────────────────────────┤
    │ Operational staff    │ Passes if their PRIMARY role matches, OR any │
    │ (doctor, pharmacist, │ of their EXTRA (multi-module) roles matches, │
    │  lab_supervisor …)   │ OR permission_flag is set and True on their  │
    │                      │ own StaffProfile (per-person grant, doesn't  │
    │                      │ depend on role at all).                     │
    └──────────────────────┴──────────────────────────────────────────────┘

    feature_flag: if set, the clinic must have that boolean flag True.
    permission_flag: if set, a person with this StaffProfile flag=True
        gets in regardless of role — e.g. permission_flag='can_access_billing'
        lets Clinic Admin grant a specific Receptionist or Lab Supervisor
        invoice access without changing their role or hardcoding it here.
    Denied access always redirects to core:home (never login — avoids loops).
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('auth:login')

            # ── SUPER ADMIN: full pass-through ────────────────────────────────
            if request.user.is_superuser:
                # Feature-flag guard still applies so superadmin respects
                # the SaaS module toggle when viewing a specific clinic.
                clinic = getattr(request, 'clinic', None)
                if feature_flag and clinic and not getattr(clinic, feature_flag, True):
                    messages.warning(
                        request,
                        f"Module not enabled for {clinic.name}."
                    )
                    return redirect('superadmin:dashboard')
                return view_func(request, *args, **kwargs)

            staff_role = getattr(request, 'staff_role', None)
            all_roles  = getattr(request, 'all_roles', [staff_role] if staff_role else [])
            clinic     = getattr(request, 'clinic', None)

            if not clinic:
                messages.error(request, 'No clinic assigned to your account.')
                return redirect('auth:login')

            # ── CLINIC ADMIN: passes ALL role checks for their clinic ──────────
            if staff_role == 'clinic_admin':
                if feature_flag and not getattr(clinic, feature_flag, True):
                    messages.warning(
                        request,
                        f"The module is not enabled for {clinic.name}. "
                        f"Contact Wahabix Support to enable it."
                    )
                    return redirect('clinic_admin:dashboard')
                return view_func(request, *args, **kwargs)

            # ── OPERATIONAL STAFF: role match (primary or extra) OR an
            #    explicit per-person permission_flag grant ──────────────────────
            has_role_match = any(r in allowed_roles for r in all_roles)
            has_permission_grant = bool(
                permission_flag and getattr(getattr(request, 'staff_profile_obj', None), permission_flag, False)
            )
            if not has_role_match and not has_permission_grant:
                messages.error(
                    request,
                    f"Access denied. This area requires: "
                    f"{', '.join(r.replace('_', ' ').title() for r in allowed_roles)}."
                )
                return redirect('core:home')

            if feature_flag and not getattr(clinic, feature_flag, True):
                messages.warning(
                    request,
                    f"This module is not enabled for {clinic.name}."
                )
                return redirect('core:home')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
