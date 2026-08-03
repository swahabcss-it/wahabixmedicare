from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from apps.core.models import Clinic, StaffProfile, AuditLog
from apps.core.decorators import role_required
from apps.core.submodules import SUBMODULE_REGISTRY, clinic_enabled_submodules

# Clinic Admins can provision every operational role except another
# Clinic Admin — granting clinic-head level access stays a Super Admin
# decision so a clinic admin can never silently create a peer who could
# lock them out, and can't promote themselves either.
ASSIGNABLE_ROLES = [r for r in StaffProfile.ROLES if r[0] != 'clinic_admin']


@role_required('clinic_admin')
def dashboard(request):
    if request.user.is_superuser and not request.clinic:
        return redirect('superadmin:clinic_list')

    clinic = request.clinic
    staff = StaffProfile.objects.filter(clinic=clinic).select_related('user')
    role_breakdown = []
    for code, label in StaffProfile.ROLES:
        count = staff.filter(role=code).count()
        if count:
            role_breakdown.append((label, count))

    quick_stats = {'patients_today': None, 'tokens_today': None}
    if clinic.is_reception_enabled:
        try:
            from apps.reception.models import Patient, Token
            today = timezone.now().date()
            quick_stats['patients_today'] = Patient.objects.filter(clinic=clinic, created_at__date=today).count()
            quick_stats['tokens_today'] = Token.objects.filter(clinic=clinic, visit_date=today).count()
        except Exception:
            pass

    context = {
        'clinic': clinic,
        'total_staff': staff.count(),
        'active_staff': staff.filter(is_active=True).count(),
        'role_breakdown': role_breakdown,
        'quick_stats': quick_stats,
        'recent_staff': staff.order_by('-id')[:5],
        'recent_logs': AuditLog.objects.filter(clinic=clinic).select_related('user').order_by('-timestamp')[:8],
        'modules': clinic.enabled_modules(),
    }
    return render(request, 'clinic_admin/dashboard.html', context)


@role_required('clinic_admin')
def staff_list(request):
    if request.user.is_superuser and not request.clinic:
        return redirect('superadmin:staff_list')
    staff = StaffProfile.objects.filter(clinic=request.clinic).select_related('user').order_by('-id')
    return render(request, 'clinic_admin/staff_list.html', {'staff': staff})


@role_required('clinic_admin')
def staff_create(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        if role not in dict(ASSIGNABLE_ROLES):
            messages.error(request, 'Invalid role selected.')
            return render(request, 'clinic_admin/staff_form.html', {'action': 'Create', 'roles': ASSIGNABLE_ROLES, 'staff_extra_roles': []})

        username = request.POST.get('username', '').strip()
        if not username or User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" is invalid or already taken.')
            return render(request, 'clinic_admin/staff_form.html', {'action': 'Create', 'roles': ASSIGNABLE_ROLES, 'staff_extra_roles': []})

        user = User.objects.create_user(
            username=username,
            password=request.POST.get('password'),
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', ''),
            email=request.POST.get('email', ''),
        )
        extra_roles_list = [r for r in request.POST.getlist('extra_roles') if r in dict(ASSIGNABLE_ROLES) and r != role]
        StaffProfile.objects.create(
            user=user, clinic=request.clinic, role=role,
            phone=request.POST.get('phone', ''),
            cnic=request.POST.get('cnic', ''),
            can_delete_lab_results=bool(request.POST.get('can_delete_lab_results')),
            can_edit_lab_catalog=bool(request.POST.get('can_edit_lab_catalog')),
            can_access_billing=bool(request.POST.get('can_access_billing')),
            extra_roles=','.join(extra_roles_list),
        )
        AuditLog.log(f'Clinic Admin created staff: {user.username}', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Staff member "{user.get_full_name() or username}" created!')
        return redirect('clinic_admin:staff_list')
    return render(request, 'clinic_admin/staff_form.html', {'action': 'Create', 'roles': ASSIGNABLE_ROLES, 'staff_extra_roles': []})


@role_required('clinic_admin')
def staff_edit(request, pk):
    staff = get_object_or_404(StaffProfile.objects.select_related('user'), pk=pk, clinic=request.clinic)
    is_self = staff.user == request.user
    if staff.role == 'clinic_admin' and not is_self:
        messages.error(request, 'Only Super Admin can manage other Clinic Admin accounts.')
        return redirect('clinic_admin:staff_list')

    if request.method == 'POST':
        user = staff.user
        new_username = request.POST.get('username', '').strip()
        submodule_context = {
            'submodule_registry': SUBMODULE_REGISTRY,
            'clinic_submodules': clinic_enabled_submodules(request.clinic),
        }
        if new_username and new_username != user.username and User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            messages.error(request, f'Username "{new_username}" is already taken.')
            return render(request, 'clinic_admin/staff_form.html', {'staff': staff, 'action': 'Edit', 'roles': ASSIGNABLE_ROLES, 'is_self': is_self, 'staff_extra_roles': staff.get_extra_roles_list(), **submodule_context})
        if new_username:
            user.username = new_username
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)

        new_password = request.POST.get('password', '').strip()
        if new_password:
            user.set_password(new_password)

        staff.phone = request.POST.get('phone', staff.phone)
        staff.cnic = request.POST.get('cnic', staff.cnic)
        staff.can_delete_lab_results = bool(request.POST.get('can_delete_lab_results'))
        staff.can_edit_lab_catalog = bool(request.POST.get('can_edit_lab_catalog'))
        staff.can_access_billing = bool(request.POST.get('can_access_billing'))
        extra_roles_list = [r for r in request.POST.getlist('extra_roles') if r in dict(ASSIGNABLE_ROLES) and r != staff.role]
        staff.extra_roles = ','.join(extra_roles_list)

        # Sub-module assignment: a Clinic Admin can only grant a sub-module
        # that the clinic's own subscription (Super Admin layer) already
        # allows — checked against clinic_enabled_submodules(), not just
        # trusted from the submitted form, so a tampered POST can't grant
        # access beyond what Super Admin licensed for this clinic.
        clinic_level = clinic_enabled_submodules(request.clinic)
        new_submodules = {}
        for module, items in SUBMODULE_REGISTRY.items():
            module_map = {}
            for key, _label in items:
                if clinic_level.get(module, {}).get(key) and request.POST.get(f'sub_{module}_{key}') == 'on':
                    module_map[key] = True
            if module_map:
                new_submodules[module] = module_map
        staff.enabled_submodules = new_submodules

        # A clinic admin can deactivate operational staff, but never their
        # own account from this form (that would lock them out instantly).
        if not is_self:
            is_active = bool(request.POST.get('is_active'))
            user.is_active = is_active
            staff.is_active = is_active
            role = request.POST.get('role')
            if role in dict(ASSIGNABLE_ROLES):
                staff.role = role

        user.save()
        staff.save()
        AuditLog.log(f'Clinic Admin updated staff: {user.username}', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Staff member "{user.get_full_name() or user.username}" updated!' + (' Password changed.' if new_password else ''))
        return redirect('clinic_admin:staff_list')

    return render(request, 'clinic_admin/staff_form.html', {
        'staff': staff, 'action': 'Edit', 'roles': ASSIGNABLE_ROLES, 'is_self': is_self,
        'staff_extra_roles': staff.get_extra_roles_list(),
        'submodule_registry': SUBMODULE_REGISTRY,
        'clinic_submodules': clinic_enabled_submodules(request.clinic),
    })


@role_required('clinic_admin')
def clinic_profile(request):
    if request.user.is_superuser and not request.clinic:
        return redirect('superadmin:clinic_list')
    clinic = request.clinic
    if request.method == 'POST':
        clinic.name = request.POST.get('name', clinic.name)
        clinic.phone = request.POST.get('phone', clinic.phone)
        clinic.email = request.POST.get('email', clinic.email)
        clinic.address = request.POST.get('address', clinic.address)
        if request.FILES.get('logo'):
            clinic.logo = request.FILES.get('logo')
        clinic.save()
        AuditLog.log(f'Clinic profile updated: {clinic.name}', user=request.user, clinic=clinic, request=request)
        messages.success(request, 'Clinic profile updated!')
        return redirect('clinic_admin:clinic_profile')
    return render(request, 'clinic_admin/clinic_profile.html', {'clinic': clinic})
