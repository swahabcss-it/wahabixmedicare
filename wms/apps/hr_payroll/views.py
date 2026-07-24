from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from apps.core.decorators import role_required
from apps.core.models import AuditLog, StaffProfile
from .models import Employee, PayrollSlip
import calendar


@role_required('hr_manager', feature_flag='is_hr_enabled')
def dashboard(request):
    clinic = request.clinic
    employees = Employee.objects.filter(clinic=clinic)
    today = timezone.now()
    recent_slips = PayrollSlip.objects.filter(clinic=clinic).select_related('employee__user').order_by('-year', '-month')[:8]
    context = {
        'total_employees': employees.count(),
        'active_employees': employees.filter(is_active=True).count(),
        'dept_counts': [(d[1], employees.filter(department=d[0]).count()) for d in Employee.DEPT if employees.filter(department=d[0]).exists()],
        'recent_slips': recent_slips,
        'current_month': today.strftime('%B %Y'),
    }
    return render(request, 'hr_payroll/dashboard.html', context)


@role_required('hr_manager', feature_flag='is_hr_enabled')
def employee_list(request):
    employees = Employee.objects.filter(clinic=request.clinic).select_related('user').order_by('department', 'designation')
    return render(request, 'hr_payroll/employee_list.html', {'employees': employees})


@role_required('hr_manager', feature_flag='is_hr_enabled')
def employee_create(request):
    from apps.core.models import User
    staff = StaffProfile.objects.filter(clinic=request.clinic).select_related('user')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        try:
            from django.contrib.auth.models import User
            user = User.objects.get(pk=user_id)
        except Exception:
            messages.error(request, 'Invalid user selected.')
            return redirect('hr_payroll:employee_list')
        if Employee.all_objects.filter(user=user, clinic=request.clinic).exists():
            messages.error(request, 'An employee record already exists for this user.')
            return redirect('hr_payroll:employee_list')
        eid = f"EMP{request.clinic.pk:02d}{Employee.objects.filter(clinic=request.clinic).count()+1:04d}"
        Employee.objects.create(
            clinic=request.clinic, user=user,
            department=request.POST.get('department'),
            designation=request.POST.get('designation'),
            employee_id=eid,
            cnic=request.POST.get('cnic', ''),
            phone=request.POST.get('phone', ''),
            address=request.POST.get('address', ''),
            basic_salary=request.POST.get('basic_salary'),
            join_date=request.POST.get('join_date'),
            created_by=request.user,
        )
        messages.success(request, f'Employee record created for {user.get_full_name()}!')
        return redirect('hr_payroll:employee_list')
    return render(request, 'hr_payroll/employee_form.html', {'action': 'Add', 'staff': staff})


@role_required('hr_manager', feature_flag='is_hr_enabled')
def payroll_list(request):
    slips = PayrollSlip.objects.filter(clinic=request.clinic).select_related('employee__user').order_by('-year', '-month', 'employee__user__first_name')
    return render(request, 'hr_payroll/payroll_list.html', {'slips': slips})


@role_required('hr_manager', feature_flag='is_hr_enabled')
def payroll_generate(request):
    employees = Employee.objects.filter(clinic=request.clinic, is_active=True)
    now = timezone.now()
    if request.method == 'POST':
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
        created_count = 0
        for emp in employees:
            if PayrollSlip.all_objects.filter(employee=emp, month=month, year=year).exists():
                continue
            allowances = float(request.POST.get(f'allowances_{emp.pk}', 0) or 0)
            bonus = float(request.POST.get(f'bonus_{emp.pk}', 0) or 0)
            deductions = float(request.POST.get(f'deductions_{emp.pk}', 0) or 0)
            tax = float(request.POST.get(f'tax_{emp.pk}', 0) or 0)
            net = float(emp.basic_salary) + allowances + bonus - deductions - tax
            PayrollSlip.objects.create(
                clinic=request.clinic, employee=emp,
                month=month, year=year,
                basic_salary=emp.basic_salary,
                allowances=allowances, bonus=bonus,
                deductions=deductions, tax=tax,
                net_salary=max(0, net),
                created_by=request.user,
            )
            created_count += 1
        AuditLog.log(f'Payroll generated for {calendar.month_name[month]} {year}: {created_count} slips', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'{created_count} payroll slips generated for {calendar.month_name[month]} {year}!')
        return redirect('hr_payroll:payroll_list')
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    return render(request, 'hr_payroll/payroll_generate.html', {'employees': employees, 'months': months, 'current_month': now.month, 'current_year': now.year})


# ─── PDF ──────────────────────────────────────────────────────────────────────
@role_required('hr_manager', feature_flag='is_hr_enabled')
def payroll_slip_pdf(request, pk):
    """Generate payroll slip PDF."""
    from apps.core.services.pdf_service import PayrollSlipPDF
    slip = get_object_or_404(PayrollSlip, pk=pk, clinic=request.clinic)
    pdf = PayrollSlipPDF(slip, request.clinic, generated_by=request.user.get_full_name())
    return pdf.as_response()
