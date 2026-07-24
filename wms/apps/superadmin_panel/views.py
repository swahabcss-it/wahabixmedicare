from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.text import slugify
from apps.core.models import Clinic, StaffProfile, AuditLog

def is_superadmin(user):
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def dashboard(request):
    clinics = Clinic.objects.all().order_by('-created_at')
    try:
        from apps.reception.models import Patient
        total_patients = Patient.all_objects.count()
    except: total_patients = 0
    context = {
        'clinics': clinics,
        'total_clinics': clinics.count(),
        'active_clinics': clinics.filter(is_active=True, is_suspended=False).count(),
        'suspended_clinics': clinics.filter(is_suspended=True).count(),
        'total_staff': StaffProfile.objects.count(),
        'total_patients': total_patients,
        'total_logs': AuditLog.objects.count(),
        'recent_logs': AuditLog.objects.select_related('user','clinic').order_by('-timestamp')[:10],
    }
    return render(request, 'superadmin/dashboard.html', context)

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def clinic_list(request):
    clinics = Clinic.objects.all().order_by('-created_at')
    return render(request, 'superadmin/clinic_list.html', {'clinics': clinics})

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def clinic_create(request):
    if request.method == 'POST':
        name = request.POST.get('name','').strip()
        slug = slugify(name)
        base_slug, counter = slug, 1
        while Clinic.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"; counter += 1
        clinic = Clinic.objects.create(
            name=name, slug=slug,
            phone=request.POST.get('phone',''),
            email=request.POST.get('email',''),
            address=request.POST.get('address',''),
            plan=request.POST.get('plan','professional'),
            plan_expires=request.POST.get('plan_expires') or None,
            logo=request.FILES.get('logo'),
            is_lab_enabled=bool(request.POST.get('is_lab_enabled')),
            is_pharmacy_enabled=bool(request.POST.get('is_pharmacy_enabled')),
            is_hr_enabled=bool(request.POST.get('is_hr_enabled')),
            is_reception_enabled=bool(request.POST.get('is_reception_enabled')),
            is_doctor_enabled=bool(request.POST.get('is_doctor_enabled')),
            is_billing_enabled=bool(request.POST.get('is_billing_enabled')),
            is_assets_enabled=bool(request.POST.get('is_assets_enabled')),
        )
        AuditLog.log(f'Created clinic: {clinic.name}', user=request.user, clinic=clinic, request=request)
        messages.success(request, f'Clinic "{clinic.name}" registered successfully!')
        return redirect('superadmin:clinic_list')
    return render(request, 'superadmin/clinic_form.html', {'action': 'Create'})

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def clinic_edit(request, pk):
    clinic = get_object_or_404(Clinic, pk=pk)
    if request.method == 'POST':
        clinic.name = request.POST.get('name', clinic.name)
        clinic.phone = request.POST.get('phone', clinic.phone)
        clinic.email = request.POST.get('email', clinic.email)
        clinic.address = request.POST.get('address', clinic.address)
        clinic.plan = request.POST.get('plan', clinic.plan)
        clinic.plan_expires = request.POST.get('plan_expires') or None
        if request.FILES.get('logo'): clinic.logo = request.FILES.get('logo')
        clinic.is_lab_enabled = bool(request.POST.get('is_lab_enabled'))
        clinic.is_pharmacy_enabled = bool(request.POST.get('is_pharmacy_enabled'))
        clinic.is_hr_enabled = bool(request.POST.get('is_hr_enabled'))
        clinic.is_reception_enabled = bool(request.POST.get('is_reception_enabled'))
        clinic.is_doctor_enabled = bool(request.POST.get('is_doctor_enabled'))
        clinic.is_billing_enabled = bool(request.POST.get('is_billing_enabled'))
        clinic.is_assets_enabled = bool(request.POST.get('is_assets_enabled'))
        clinic.save()
        AuditLog.log(f'Updated clinic: {clinic.name}', user=request.user, clinic=clinic, request=request)
        messages.success(request, f'Clinic "{clinic.name}" updated!')
        return redirect('superadmin:clinic_list')
    return render(request, 'superadmin/clinic_form.html', {'clinic': clinic, 'action': 'Edit'})

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def clinic_detail(request, pk):
    clinic = get_object_or_404(Clinic, pk=pk)
    staff = StaffProfile.objects.filter(clinic=clinic).select_related('user')
    modules = [
        ('lab', '🔬', 'Laboratory', clinic.is_lab_enabled),
        ('pharmacy', '💊', 'Pharmacy', clinic.is_pharmacy_enabled),
        ('hr', '👥', 'HR & Payroll', clinic.is_hr_enabled),
        ('reception', '🏪', 'Reception', clinic.is_reception_enabled),
        ('doctor', '👨‍⚕️', 'Doctor', clinic.is_doctor_enabled),
        ('billing', '💳', 'Billing', clinic.is_billing_enabled),
        ('assets', '🛠️', 'Assets', clinic.is_assets_enabled),
    ]
    return render(request, 'superadmin/clinic_detail.html', {'clinic': clinic, 'staff': staff, 'modules': modules})

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def clinic_toggle_suspend(request, pk):
    clinic = get_object_or_404(Clinic, pk=pk)
    clinic.is_suspended = not clinic.is_suspended
    clinic.is_active = not clinic.is_suspended
    clinic.save()
    status = 'suspended' if clinic.is_suspended else 'activated'
    AuditLog.log(f'Clinic {status}: {clinic.name}', user=request.user, clinic=clinic, request=request)
    messages.success(request, f'Clinic "{clinic.name}" has been {status}.')
    return redirect(request.META.get('HTTP_REFERER', 'superadmin:clinic_list'))

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def staff_list(request):
    staff = StaffProfile.objects.all().select_related('user','clinic').order_by('-id')
    return render(request, 'superadmin/staff_list.html', {'staff': staff})

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def staff_create(request):
    clinics = Clinic.objects.filter(is_active=True)
    preselect = request.GET.get('clinic')
    if request.method == 'POST':
        clinic_id = request.POST.get('clinic')
        clinic = get_object_or_404(Clinic, pk=clinic_id)
        username = request.POST.get('username','').strip()
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists.')
            return render(request, 'superadmin/staff_form.html', {'clinics': clinics, 'action': 'Create', 'staff_extra_roles': []})
        user = User.objects.create_user(
            username=username,
            password=request.POST.get('password'),
            first_name=request.POST.get('first_name',''),
            last_name=request.POST.get('last_name',''),
            email=request.POST.get('email',''),
        )
        VALID_ROLES = ['clinic_admin','doctor','lab_supervisor','pharmacist','receptionist','hr_manager','accountant']
        role = request.POST.get('role')
        extra_roles_list = [r for r in request.POST.getlist('extra_roles') if r in VALID_ROLES and r != role]
        StaffProfile.objects.create(
            user=user, clinic=clinic,
            role=role,
            phone=request.POST.get('phone',''),
            cnic=request.POST.get('cnic',''),
            can_delete_lab_results=bool(request.POST.get('can_delete_lab_results')),
            can_access_billing=bool(request.POST.get('can_access_billing')),
            extra_roles=','.join(extra_roles_list),
        )
        AuditLog.log(f'Created staff: {user.username} at {clinic.name}', user=request.user, clinic=clinic, request=request)
        messages.success(request, f'Staff member "{user.get_full_name()}" created!')
        return redirect('superadmin:staff_list')
    return render(request, 'superadmin/staff_form.html', {'clinics': clinics, 'action': 'Create', 'preselect': preselect, 'staff_extra_roles': []})

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def staff_edit(request, pk):
    staff = get_object_or_404(StaffProfile.objects.select_related('user', 'clinic'), pk=pk)
    clinics = Clinic.objects.filter(is_active=True)
    if request.method == 'POST':
        user = staff.user
        new_username = request.POST.get('username', '').strip()
        if new_username and new_username != user.username and User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            messages.error(request, f'Username "{new_username}" is already taken.')
            return render(request, 'superadmin/staff_form.html', {'staff': staff, 'clinics': clinics, 'action': 'Edit', 'staff_extra_roles': staff.get_extra_roles_list()})
        if new_username:
            user.username = new_username
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)

        new_password = request.POST.get('password', '').strip()
        if new_password:
            user.set_password(new_password)

        is_active = bool(request.POST.get('is_active'))
        user.is_active = is_active
        user.save()

        clinic_id = request.POST.get('clinic')
        if clinic_id:
            staff.clinic = get_object_or_404(Clinic, pk=clinic_id)
        staff.role = request.POST.get('role', staff.role)
        staff.phone = request.POST.get('phone', staff.phone)
        staff.cnic = request.POST.get('cnic', staff.cnic)
        staff.can_delete_lab_results = bool(request.POST.get('can_delete_lab_results'))
        staff.can_access_billing = bool(request.POST.get('can_access_billing'))
        VALID_ROLES = ['clinic_admin','doctor','lab_supervisor','pharmacist','receptionist','hr_manager','accountant']
        extra_roles_list = [r for r in request.POST.getlist('extra_roles') if r in VALID_ROLES and r != staff.role]
        staff.extra_roles = ','.join(extra_roles_list)
        staff.is_active = is_active
        staff.save()

        AuditLog.log(f'Updated staff: {user.username}', user=request.user, clinic=staff.clinic, request=request)
        messages.success(request, f'Staff member "{user.get_full_name() or user.username}" updated!' + (' Password changed.' if new_password else ''))
        return redirect('superadmin:staff_list')
    return render(request, 'superadmin/staff_form.html', {'staff': staff, 'clinics': clinics, 'action': 'Edit', 'staff_extra_roles': staff.get_extra_roles_list()})

@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def audit_logs(request):
    logs = AuditLog.objects.select_related('user','clinic').order_by('-timestamp')[:200]
    return render(request, 'superadmin/audit_logs.html', {'logs': logs})


# ─── CLINIC CONTEXT SWITCHER ─────────────────────────────────────────────────
@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def clinic_enter(request, pk):
    """
    Super Admin enters a clinic's operational context.
    Sets session['active_clinic_id'] so middleware injects request.clinic
    into all subsequent requests, giving the superadmin full access to
    every module of that specific tenant.
    """
    clinic = get_object_or_404(Clinic, pk=pk)
    request.session['active_clinic_id'] = clinic.pk
    messages.success(
        request,
        f'📍 Now viewing <strong>{clinic.name}</strong> as Super Admin. '
        f'You have full access to all clinic modules.'
    )
    return redirect('core:home')


@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def clinic_exit(request):
    """
    Super Admin exits the current clinic context, returning to the
    global superadmin dashboard with no tenant scope active.
    """
    clinic_name = ''
    active_id = request.session.pop('active_clinic_id', None)
    if active_id:
        try:
            clinic_name = Clinic.objects.get(pk=active_id).name
        except Exception:
            pass
    if clinic_name:
        messages.info(request, f'Exited clinic view: {clinic_name}')
    return redirect('superadmin:dashboard')


@login_required
@user_passes_test(is_superadmin, login_url='/auth/login/')
def platform_settings(request):
    """
    Platform-wide settings — currently just the theme. Deliberately the
    ONLY place theme can be changed, and only a superuser can reach it.
    Applies instantly to every clinic and the login page, for everyone.
    """
    from apps.core.models import PlatformSettings
    settings_obj = PlatformSettings.get()

    if request.method == 'POST':
        new_theme = request.POST.get('theme')
        valid_themes = [choice[0] for choice in PlatformSettings.THEMES]
        if new_theme in valid_themes:
            settings_obj.theme = new_theme
            settings_obj.save()
            AuditLog.log(f'Platform theme changed to "{new_theme}"', user=request.user, request=request)
            messages.success(request, f'Platform theme updated to "{dict(PlatformSettings.THEMES)[new_theme]}" for everyone.')
        return redirect('superadmin:platform_settings')

    return render(request, 'superadmin/platform_settings.html', {
        'settings_obj': settings_obj,
        'themes': PlatformSettings.THEMES,
    })
