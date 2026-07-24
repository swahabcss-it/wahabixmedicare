from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
import json
from apps.core.decorators import role_required
from apps.core.models import AuditLog
from .models import LabTestCatalog, LabOrder, LabResult
from apps.reception.models import Patient
import uuid


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def dashboard(request):
    clinic = request.clinic
    tests = LabTestCatalog.objects.filter(clinic=clinic).count()
    orders = LabOrder.objects.filter(clinic=clinic)
    context = {
        'total_tests': tests,
        'pending_orders': orders.filter(status='pending').count(),
        'processing_orders': orders.filter(status='processing').count(),
        'completed_orders': orders.filter(status='completed').count(),
        'recent_orders': orders.select_related('patient').order_by('-ordered_at')[:10],
    }
    return render(request, 'lab/dashboard.html', context)


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def test_catalog(request):
    tests = LabTestCatalog.objects.filter(clinic=request.clinic).order_by('test_name')
    return render(request, 'lab/test_catalog.html', {'tests': tests})


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def test_create(request):
    if request.method == 'POST':
        LabTestCatalog.objects.create(
            clinic=request.clinic,
            test_name=request.POST.get('test_name'),
            test_code=request.POST.get('test_code', '').upper(),
            rate=request.POST.get('rate'),
            reference_range=request.POST.get('reference_range', ''),
            unit=request.POST.get('unit', ''),
            sample_type=request.POST.get('sample_type', ''),
            category=request.POST.get('category', 'clinical_chemistry'),
            created_by=request.user,
        )
        messages.success(request, 'Lab test added to catalog!')
        return redirect('laboratory:test_catalog')
    return render(request, 'lab/test_form.html', {'action': 'Add'})


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def test_edit(request, pk):
    test = get_object_or_404(LabTestCatalog, pk=pk, clinic=request.clinic)
    if request.method == 'POST':
        test.test_name = request.POST.get('test_name', test.test_name)
        test.test_code = request.POST.get('test_code', test.test_code).upper()
        test.rate = request.POST.get('rate', test.rate)
        test.reference_range = request.POST.get('reference_range', test.reference_range)
        test.unit = request.POST.get('unit', test.unit)
        test.sample_type = request.POST.get('sample_type', test.sample_type)
        test.category = request.POST.get('category', test.category)
        test.save()
        messages.success(request, f'Test "{test.test_name}" updated!')
        return redirect('laboratory:test_catalog')
    return render(request, 'lab/test_form.html', {'action': 'Edit', 'test': test})


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def test_soft_delete(request, pk):
    """Soft delete only if the Lab Supervisor has been granted delete permission by Clinic Admin."""
    try:
        profile = request.user.staff_profile
    except Exception:
        messages.error(request, 'Permission error.')
        return redirect('laboratory:test_catalog')
    if not profile.can_delete_lab_results:
        messages.error(request, '⛔ Your Clinic Admin has not granted you deletion access.')
        return redirect('laboratory:test_catalog')
    test = get_object_or_404(LabTestCatalog, pk=pk, clinic=request.clinic)
    test.soft_delete(user=request.user)
    AuditLog.log(f'Lab test soft-deleted: {test.test_name}', user=request.user, clinic=request.clinic, request=request)
    messages.success(request, f'Test "{test.test_name}" removed from catalog.')
    return redirect('laboratory:test_catalog')


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def order_list(request):
    orders = LabOrder.objects.filter(clinic=request.clinic).select_related('patient').order_by('-ordered_at')
    return render(request, 'lab/order_list.html', {'orders': orders})


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def order_create(request):
    if request.method == 'POST':
        patient = get_object_or_404(Patient, pk=request.POST.get('patient_id'), clinic=request.clinic)
        test_ids = request.POST.getlist('tests')
        tests = LabTestCatalog.objects.filter(pk__in=test_ids, clinic=request.clinic)
        total = sum(t.rate for t in tests)
        voucher = uuid.uuid4().hex[:8].upper()
        order = LabOrder.objects.create(
            clinic=request.clinic, patient=patient,
            voucher_code=voucher, total_amount=total,
            doctor_name=request.POST.get('doctor_name', ''),
            created_by=request.user,
        )
        order.tests.set(tests)
        AuditLog.log(f'Lab order created: {voucher} for {patient.full_name}', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Lab order created! Voucher: {voucher}')
        return redirect('laboratory:order_list')
    patients = Patient.objects.filter(clinic=request.clinic).order_by('full_name')
    tests = LabTestCatalog.objects.filter(clinic=request.clinic)
    return render(request, 'lab/order_form.html', {'patients': patients, 'tests': tests})


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def mark_sample_collected(request, order_pk):
    """
    Sample can only be marked collected once payment has cleared — this
    is the gate the person asked for: if a doctor-ordered test's invoice
    is still unpaid, this action is blocked (button doesn't even show in
    the template, but the view re-checks server-side too since a URL can
    always be hit directly).
    """
    order = get_object_or_404(LabOrder, pk=order_pk, clinic=request.clinic)
    if not order.is_payment_cleared:
        messages.error(request, f'Cannot collect sample for {order.voucher_code} — payment is still pending at Reception.')
        return redirect('laboratory:order_list')

    if request.method == 'POST':
        order.sample_collected = True
        order.sample_collected_at = timezone.now()
        order.sample_collected_by = request.user
        order.status = 'processing'
        order.save(update_fields=['sample_collected', 'sample_collected_at', 'sample_collected_by', 'status'])
        AuditLog.log(f'Sample collected for order {order.voucher_code}', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Sample collected for {order.voucher_code}. Results can now be entered.')
    return redirect('laboratory:order_list')


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def result_entry(request, order_pk):
    order = get_object_or_404(LabOrder, pk=order_pk, clinic=request.clinic)
    if not order.can_enter_results and order.status not in ('completed', 'delivered'):
        messages.error(request, f'Sample for {order.voucher_code} hasn\'t been collected yet — mark it collected first.')
        return redirect('laboratory:order_list')
    if request.method == 'POST':
        for test in order.tests.all():
            val = request.POST.get(f'result_{test.pk}', '').strip()
            remarks = request.POST.get(f'remarks_{test.pk}', '').strip()
            is_abnormal = bool(request.POST.get(f'abnormal_{test.pk}'))
            if val:
                LabResult.objects.update_or_create(
                    order=order, test=test, clinic=request.clinic,
                    defaults=dict(
                        result_value=val,
                        remarks=remarks,
                        is_abnormal=is_abnormal,
                        created_by=request.user,
                    ),
                )
        order.status = 'completed'
        order.save()
        AuditLog.log(f'Lab results entered for order {order.voucher_code}', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Results saved for voucher {order.voucher_code}. Order marked complete.')

        from apps.core.services.notifications import notify_lab_report_ready
        notify_lab_report_ready(order)
        return redirect('laboratory:order_list')
    existing_results = {r.test_id: r for r in LabResult.objects.filter(order=order)}
    tests_with_results = [(test, existing_results.get(test.pk)) for test in order.tests.all()]
    return render(request, 'lab/result_entry.html', {'order': order, 'tests_with_results': tests_with_results})


# ─── SMART VERIFICATION & QR ───────────────────────────────────────────────────
@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def order_verify(request, order_pk):
    order = get_object_or_404(LabOrder, pk=order_pk, clinic=request.clinic)
    order.results.update(is_locked=True, locked_at=timezone.now())
    order.is_verified = True
    order.verified_at = timezone.now()
    order.status = 'completed'
    order.save()
    AuditLog.log(f'Lab order verified & QR-locked: {order.voucher_code}', user=request.user, clinic=request.clinic, request=request)
    messages.success(request, f'✅ Order {order.voucher_code} verified. QR-secured report ready to print/share.')
    return redirect('laboratory:result_pdf', order_pk=order.pk)


def verify_report_public(request, voucher_code, verification_hash):
    order = LabOrder.objects.filter(voucher_code=voucher_code, verification_hash=verification_hash, is_verified=True).first()
    if not order:
        return render(request, 'lab/verify_result.html', {'valid': False})
    return render(request, 'lab/verify_result.html', {
        'valid': True, 'order': order, 'patient_name': order.patient.full_name,
        'verified_at': order.verified_at,
    })


@csrf_exempt
def analyzer_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    api_key = request.headers.get('X-Analyzer-Key', '')
    if api_key != settings.ANALYZER_API_KEY:
        return HttpResponseForbidden('Invalid analyzer API key.')
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    from apps.core.models import Clinic
    clinic = Clinic.objects.filter(slug=payload.get('clinic_slug')).first()
    if not clinic:
        return JsonResponse({'error': 'Unknown clinic_slug'}, status=404)
    order = LabOrder.objects.filter(clinic=clinic, voucher_code=payload.get('voucher_code')).first()
    if not order:
        return JsonResponse({'error': 'Unknown voucher_code'}, status=404)
    test = LabTestCatalog.objects.filter(clinic=clinic, test_code=payload.get('test_code')).first()
    if not test:
        return JsonResponse({'error': 'Unknown test_code'}, status=404)

    result, _ = LabResult.objects.update_or_create(
        order=order, test=test, clinic=clinic,
        defaults=dict(
            result_value=str(payload.get('result_value', '')),
            is_abnormal=bool(payload.get('is_abnormal', False)),
            source='analyzer',
        ),
    )
    if order.status == 'pending':
        order.status = 'processing'
        order.save()
    AuditLog.log(f'Analyzer pushed result for {test.test_name} on order {order.voucher_code}', clinic=clinic, model_name='LabResult', object_id=result.pk)
    return JsonResponse({'success': True, 'result_id': result.pk})


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def order_soft_delete(request, pk):
    try:
        profile = request.user.staff_profile
    except Exception:
        messages.error(request, 'Permission error.')
        return redirect('laboratory:order_list')
    if not profile.can_delete_lab_results:
        messages.error(request, '⛔ Your Clinic Admin has not granted you deletion access.')
        return redirect('laboratory:order_list')
    order = get_object_or_404(LabOrder, pk=pk, clinic=request.clinic)
    order.soft_delete(user=request.user)
    AuditLog.log(f'Lab order soft-deleted: {order.voucher_code}', user=request.user, clinic=request.clinic, request=request)
    messages.success(request, f'Order {order.voucher_code} archived (audit trail preserved).')
    return redirect('laboratory:order_list')


@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def result_soft_delete(request, pk):
    try:
        profile = request.user.staff_profile
    except Exception:
        messages.error(request, 'Permission error.')
        return redirect('laboratory:order_list')
    if not profile.can_delete_lab_results:
        messages.error(request, '⛔ Your Clinic Admin has not granted you deletion access.')
        return redirect('laboratory:order_list')
    result = get_object_or_404(LabResult, pk=pk, clinic=request.clinic)
    order_pk = result.order_id
    result.soft_delete(user=request.user)
    AuditLog.log(f'Lab result soft-deleted: {result.test.test_name}', user=request.user, clinic=request.clinic, request=request)
    messages.success(request, 'Result archived — not permanently deleted, audit trail preserved.')
    return redirect('laboratory:result_entry', order_pk=order_pk)


# ─── PDF REPORT ───────────────────────────────────────────────────────────────
@role_required('lab_supervisor', feature_flag='is_lab_enabled')
def result_pdf(request, order_pk):
    """Generate professional lab report PDF with clinic branding — inline or download."""
    from apps.core.services.pdf_service import LabReportPDF
    order = get_object_or_404(LabOrder, pk=order_pk, clinic=request.clinic)
    pdf = LabReportPDF(order, request.clinic, generated_by=request.user.get_full_name())
    if request.GET.get('download'):
        return pdf.as_download_response()
    return pdf.as_response()
