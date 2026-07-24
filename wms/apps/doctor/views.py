from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import models
from apps.core.decorators import role_required
from apps.core.models import AuditLog
from apps.reception.models import Token, Patient
from .models import DoctorProfile, Prescription, PrescriptionMedicine, TreatmentTemplate


def _doctor_profile(request):
    try:
        return DoctorProfile.objects.get(user=request.user, clinic=request.clinic)
    except DoctorProfile.DoesNotExist:
        return None


@role_required('doctor', feature_flag='is_doctor_enabled')
def dashboard(request):
    today = timezone.now().date()
    profile = _doctor_profile(request)
    queue = Token.objects.filter(
        clinic=request.clinic, visit_date=today,
        status__in=['waiting', 'with_doctor']
    ).select_related('patient').order_by('token_number')
    recent_rx = Prescription.objects.filter(clinic=request.clinic).select_related('patient').order_by('-visit_date')[:8]
    context = {
        'profile': profile,
        'queue': queue,
        'waiting_count': queue.filter(status='waiting').count(),
        'in_room_count': queue.filter(status='with_doctor').count(),
        'done_today': Token.objects.filter(clinic=request.clinic, visit_date=today, status='done').count(),
        'recent_rx': recent_rx,
    }
    return render(request, 'doctor/dashboard.html', context)


@role_required('doctor', feature_flag='is_doctor_enabled')
def patient_queue(request):
    today = timezone.now().date()
    queue = Token.objects.filter(
        clinic=request.clinic, visit_date=today
    ).select_related('patient').order_by('token_number')
    return render(request, 'doctor/queue.html', {'queue': queue, 'today': today})


@role_required('doctor', feature_flag='is_doctor_enabled')
def call_patient(request, token_pk):
    token = get_object_or_404(Token, pk=token_pk, clinic=request.clinic)
    token.status = 'with_doctor'
    token.save()
    messages.success(request, f'Token #{token.token_number} — {token.patient.full_name} called in.')
    return redirect('doctor:queue')


@role_required('doctor', feature_flag='is_doctor_enabled')
def prescription_create(request, token_pk):
    token = get_object_or_404(Token, pk=token_pk, clinic=request.clinic)
    profile = _doctor_profile(request)
    # Auto-create a minimal DoctorProfile if doctor logged in but record missing
    if not profile:
        profile = DoctorProfile.objects.create(
            clinic=request.clinic, user=request.user,
            specialization='General Physician',
            qualification='MBBS',
            created_by=request.user,
        )
    if request.method == 'POST':
        template_id = request.POST.get('template_id') or None
        rx = Prescription.objects.create(
            clinic=request.clinic,
            patient=token.patient,
            doctor=profile,
            token=token,
            template_used_id=template_id,
            symptoms=request.POST.get('symptoms', ''),
            diagnosis=request.POST.get('diagnosis', ''),
            icd11_code=request.POST.get('icd11_code', ''),
            notes=request.POST.get('notes', ''),
            follow_up_date=request.POST.get('follow_up_date') or None,
            created_by=request.user,
        )
        names = request.POST.getlist('med_name')
        dosages = request.POST.getlist('med_dosage')
        freqs = request.POST.getlist('med_freq')
        durs = request.POST.getlist('med_duration')
        instrs = request.POST.getlist('med_instructions')
        for i, name in enumerate(names):
            if name.strip():
                PrescriptionMedicine.objects.create(
                    prescription=rx,
                    medicine_name=name.strip(),
                    dosage=dosages[i] if i < len(dosages) else '',
                    frequency=freqs[i] if i < len(freqs) else '',
                    duration=durs[i] if i < len(durs) else '',
                    instructions=instrs[i] if i < len(instrs) else '',
                )

        # ── INSTANT BACKGROUND ROUTING (Alt+P Finalize & Dispatch) ──────────
        lab_test_ids = request.POST.getlist('lab_test_ids')
        if lab_test_ids:
            from apps.laboratory.models import LabTestCatalog, LabOrder
            from apps.billing.models import Invoice, InvoiceItem
            import uuid
            tests = LabTestCatalog.objects.filter(pk__in=lab_test_ids, clinic=request.clinic)
            if tests.exists():
                total = sum(t.rate for t in tests)
                order = LabOrder.objects.create(
                    clinic=request.clinic, patient=token.patient,
                    voucher_code=uuid.uuid4().hex[:8].upper(), total_amount=total,
                    doctor_name=request.user.get_full_name() or request.user.username,
                    notes=f'Auto-routed from RX-{rx.pk:04d}',
                    created_by=request.user,
                )
                order.tests.set(tests)

                # Doctor ordering a lab test creates the invoice right away
                # — unpaid, waiting at Reception for the patient to pay on
                # their way out. Reception sees it under "Pending Lab
                # Payments" and collects it there; no separate manual
                # billing entry needed.
                count = Invoice.objects.filter(clinic=request.clinic).count() + 1
                inv_no = f"INV{timezone.now().strftime('%Y%m')}{count:04d}"
                invoice = Invoice.objects.create(
                    clinic=request.clinic, patient=token.patient,
                    invoice_number=inv_no, subtotal=total, total=total,
                    amount_paid=0, status='draft',
                    notes=f'Lab tests ordered by Dr. {request.user.get_full_name() or request.user.username} — Voucher {order.voucher_code}',
                    created_by=request.user,
                )
                for t in tests:
                    InvoiceItem.objects.create(
                        invoice=invoice, description=f'Lab Test — {t.test_name}',
                        quantity=1, unit_price=t.rate, subtotal=t.rate,
                    )
                order.invoice = invoice
                order.save(update_fields=['invoice'])

                rx.lab_order = order
                rx.dispatched_to_lab = True

        from apps.pharmacy.models import Medicine
        matched_any = any(
            n.strip() and Medicine.objects.filter(clinic=request.clinic, name__iexact=n.strip()).exists()
            for n in names
        )
        rx.dispatched_to_pharmacy = matched_any
        rx.save()

        if template_id:
            TreatmentTemplate.objects.filter(pk=template_id).update(usage_count=models.F('usage_count') + 1)

        token.status = 'done'
        token.save()
        AuditLog.log(f'Prescription RX-{rx.pk:04d} created for {token.patient.full_name} (routed: lab={rx.dispatched_to_lab}, pharmacy={rx.dispatched_to_pharmacy})', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'✅ Prescription finalized & dispatched! Token #{token.token_number} marked done.')

        from apps.core.services.notifications import notify_prescription_ready
        notify_prescription_ready(rx)

        return redirect('doctor:queue')

    templates = TreatmentTemplate.objects.filter(clinic=request.clinic, is_active=True)
    from apps.laboratory.models import LabTestCatalog
    lab_tests = LabTestCatalog.objects.filter(clinic=request.clinic)
    return render(request, 'doctor/prescription_form.html', {
        'token': token, 'profile': profile, 'templates': templates, 'lab_tests': lab_tests,
    })


@role_required('doctor', feature_flag='is_doctor_enabled')
def prescription_edit(request, pk):
    """
    Lets a doctor correct/update a prescription after saving it — e.g. a
    typo in dosage, or a medicine that needs adjusting. Deliberately does
    NOT re-trigger lab test ordering or pharmacy dispatch: those already
    happened when the prescription was first finalized, and re-running
    them here would create duplicate invoices/orders. If the lab tests
    themselves need to change, that's a new prescription/order, not an
    edit to this one.
    """
    rx = get_object_or_404(Prescription.objects.select_related('patient', 'doctor__user', 'lab_order'), pk=pk, clinic=request.clinic)

    if request.method == 'POST':
        rx.symptoms = request.POST.get('symptoms', '')
        rx.diagnosis = request.POST.get('diagnosis', '')
        rx.icd11_code = request.POST.get('icd11_code', '')
        rx.notes = request.POST.get('notes', '')
        rx.follow_up_date = request.POST.get('follow_up_date') or None
        rx.save()

        # Replace the medicine list wholesale — simpler and less error-prone
        # than trying to diff/match existing rows against submitted ones.
        rx.medicines.all().delete()
        names = request.POST.getlist('med_name')
        dosages = request.POST.getlist('med_dosage')
        freqs = request.POST.getlist('med_freq')
        durs = request.POST.getlist('med_duration')
        instrs = request.POST.getlist('med_instructions')
        for i, name in enumerate(names):
            if name.strip():
                PrescriptionMedicine.objects.create(
                    prescription=rx,
                    medicine_name=name.strip(),
                    dosage=dosages[i] if i < len(dosages) else '',
                    frequency=freqs[i] if i < len(freqs) else '',
                    duration=durs[i] if i < len(durs) else '',
                    instructions=instrs[i] if i < len(instrs) else '',
                )

        AuditLog.log(f'Prescription RX-{rx.pk:04d} edited for {rx.patient.full_name}',
                     user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Prescription RX-{rx.pk:04d} updated.')
        return redirect('doctor:prescription_detail', pk=rx.pk)

    return render(request, 'doctor/prescription_edit.html', {
        'rx': rx, 'medicines': rx.medicines.all(),
    })


@role_required('doctor', feature_flag='is_doctor_enabled')
def prescription_list(request):
    rxs = Prescription.objects.filter(clinic=request.clinic).select_related('patient', 'doctor__user').order_by('-visit_date')
    return render(request, 'doctor/prescription_list.html', {'prescriptions': rxs})


@role_required('doctor', feature_flag='is_doctor_enabled')
def prescription_detail(request, pk):
    rx = get_object_or_404(Prescription, pk=pk, clinic=request.clinic)
    medicines = rx.medicines.all()
    return render(request, 'doctor/prescription_detail.html', {'rx': rx, 'medicines': medicines})


@role_required('doctor', feature_flag='is_doctor_enabled')
def prescription_print(request, pk):
    """Standalone A4 printable Rx slip — hospital letterhead style."""
    rx = get_object_or_404(
        Prescription.objects.select_related('patient', 'doctor__user', 'token'), pk=pk, clinic=request.clinic
    )
    medicines = rx.medicines.all()
    return render(request, 'doctor/prescription_print.html', {
        'rx': rx, 'medicines': medicines, 'clinic': request.clinic, 'token': rx.token,
    })


# ─── TREATMENT TEMPLATES (1-Click Prescription Sets) ──────────────────────────
@role_required('doctor', feature_flag='is_doctor_enabled')
def template_list(request):
    templates = TreatmentTemplate.objects.filter(clinic=request.clinic)
    return render(request, 'doctor/template_list.html', {'templates': templates})


@role_required('doctor', feature_flag='is_doctor_enabled')
def template_create(request):
    from apps.laboratory.models import LabTestCatalog
    if request.method == 'POST':
        med_names = request.POST.getlist('med_name')
        med_dosages = request.POST.getlist('med_dosage')
        med_freqs = request.POST.getlist('med_freq')
        med_durations = request.POST.getlist('med_duration')
        medicines = []
        for i, n in enumerate(med_names):
            if n.strip():
                medicines.append({
                    'name': n.strip(),
                    'dosage': med_dosages[i] if i < len(med_dosages) else '',
                    'frequency': med_freqs[i] if i < len(med_freqs) else '',
                    'duration': med_durations[i] if i < len(med_durations) else '',
                })
        tmpl = TreatmentTemplate.objects.create(
            clinic=request.clinic,
            name=request.POST.get('name'),
            icon=request.POST.get('icon', '⭐'),
            icd11_code=request.POST.get('icd11_code', ''),
            diagnosis_text=request.POST.get('diagnosis_text', ''),
            chief_complaint_text=request.POST.get('chief_complaint_text', ''),
            medicines_json=medicines,
            created_by=request.user,
        )
        tmpl.lab_tests.set(request.POST.getlist('lab_test_ids'))
        messages.success(request, f'Template "{tmpl.name}" created — it will appear as a 1-click button.')
        return redirect('doctor:template_list')
    lab_tests = LabTestCatalog.objects.filter(clinic=request.clinic)
    return render(request, 'doctor/template_form.html', {'action': 'Create', 'lab_tests': lab_tests})


@role_required('doctor', feature_flag='is_doctor_enabled')
def template_delete(request, pk):
    tmpl = get_object_or_404(TreatmentTemplate, pk=pk, clinic=request.clinic)
    tmpl.soft_delete(user=request.user)
    messages.success(request, f'Template "{tmpl.name}" removed.')
    return redirect('doctor:template_list')


@role_required('doctor', feature_flag='is_doctor_enabled')
def template_apply_ajax(request, pk):
    """Returns full template payload as JSON for 1-click auto-fill on the workspace."""
    tmpl = get_object_or_404(TreatmentTemplate, pk=pk, clinic=request.clinic)
    return JsonResponse({
        'icd11_code': tmpl.icd11_code,
        'diagnosis_text': tmpl.diagnosis_text,
        'chief_complaint_text': tmpl.chief_complaint_text,
        'medicines': tmpl.medicines_json,
        'lab_test_ids': list(tmpl.lab_tests.values_list('id', flat=True)),
    })


# ─── PDF ──────────────────────────────────────────────────────────────────────
@role_required('doctor', feature_flag='is_doctor_enabled')
def prescription_pdf(request, pk):
    """Generate professional prescription PDF — inline or download."""
    from apps.core.services.pdf_service import PrescriptionPDF
    rx = get_object_or_404(Prescription, pk=pk, clinic=request.clinic)
    pdf = PrescriptionPDF(rx, request.clinic, generated_by=request.user.get_full_name())
    if request.GET.get('download'):
        return pdf.as_download_response()
    return pdf.as_response()
