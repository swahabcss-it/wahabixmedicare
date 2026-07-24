"""
Patient Portal — a lightweight, separate login system for patients
themselves (not staff). Deliberately does NOT use Django's User/auth
system: patients log in with their Patient ID (e.g. "P-0004") and a short
password Reception generates for them at registration — same pattern as
the "Username / Password" slip shown in the reference report.

Session-based: request.session['portal_patient_id'] holds the logged-in
patient's primary key. No relation at all to staff `role_required` /
StaffProfile — a patient can never accidentally end up with staff access,
and a staff login can never accidentally grant patient-portal access.
"""
from functools import wraps
from django.shortcuts import render, redirect
from django.contrib import messages
from apps.reception.models import Patient


def patient_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        patient_pk = request.session.get('portal_patient_id')
        if not patient_pk:
            return redirect('patient_portal:login')
        try:
            patient = Patient.objects.get(pk=patient_pk)
        except Patient.DoesNotExist:
            request.session.pop('portal_patient_id', None)
            return redirect('patient_portal:login')
        request.portal_patient = patient
        return view_func(request, *args, **kwargs)
    return wrapper


def login_view(request):
    if request.session.get('portal_patient_id'):
        return redirect('patient_portal:dashboard')

    if request.method == 'POST':
        patient_id_raw = request.POST.get('patient_id', '').strip().upper()
        password = request.POST.get('password', '').strip()
        pk = None
        if patient_id_raw.startswith('P-'):
            try:
                pk = int(patient_id_raw[2:])
            except ValueError:
                pk = None

        patient = Patient.objects.filter(pk=pk).first() if pk else None
        if patient and patient.check_portal_password(password):
            request.session['portal_patient_id'] = patient.pk
            request.session.set_expiry(3600 * 4)  # 4 hours — shared/public devices
            return redirect('patient_portal:dashboard')

        messages.error(request, 'Invalid Patient ID or password. Ask Reception if you\'ve lost your access slip.')

    return render(request, 'patient_portal/login.html')


def logout_view(request):
    request.session.pop('portal_patient_id', None)
    return redirect('patient_portal:login')


@patient_login_required
def dashboard(request):
    patient = request.portal_patient
    from apps.doctor.models import Prescription
    from apps.laboratory.models import LabOrder, LabResult
    from apps.billing.models import Invoice

    prescriptions = Prescription.objects.filter(patient=patient).order_by('-visit_date')
    lab_orders = LabOrder.objects.filter(
        patient=patient, status__in=['completed', 'delivered']
    ).order_by('-ordered_at').prefetch_related('tests')
    invoices = Invoice.objects.filter(patient=patient).order_by('-created_at')

    # Chughtai-style "test history" — every individual result this patient
    # has ever had, grouped by test name, most recent first, so a value
    # like HbA1c or Uric Acid can be tracked over multiple visits at a
    # glance instead of digging through separate report PDFs one by one.
    results_history = (
        LabResult.objects.filter(order__patient=patient, is_deleted=False, order__status__in=['completed', 'delivered'])
        .select_related('test', 'order')
        .order_by('test__test_name', '-order__ordered_at')
    )
    history_by_test = {}
    for r in results_history:
        history_by_test.setdefault(r.test.test_name, []).append(r)

    return render(request, 'patient_portal/dashboard.html', {
        'patient': patient,
        'prescriptions': prescriptions,
        'lab_orders': lab_orders,
        'invoices': invoices,
        'history_by_test': history_by_test,
    })


# ── Patient-scoped document views ───────────────────────────────────────
# These deliberately do NOT reuse the staff `role_required` decorator —
# a patient is never a staff member and has no StaffProfile/clinic
# session. Instead: patient_login_required (their own portal session)
# PLUS an explicit ownership check (patient=request.portal_patient) so
# one patient can never view another patient's document just by guessing
# a different ID in the URL.

@patient_login_required
def view_prescription(request, pk):
    from django.http import Http404
    from apps.doctor.models import Prescription
    from apps.core.services.pdf_service import PrescriptionPDF

    rx = Prescription.objects.filter(pk=pk, patient=request.portal_patient).select_related('doctor__user', 'patient', 'token').first()
    if not rx:
        raise Http404
    pdf = PrescriptionPDF(rx, rx.clinic)
    return pdf.as_download_response() if request.GET.get('download') else pdf.as_response()


@patient_login_required
def view_lab_report(request, pk):
    from django.http import Http404
    from apps.laboratory.models import LabOrder
    from apps.core.services.pdf_service import LabReportPDF

    order = LabOrder.objects.filter(pk=pk, patient=request.portal_patient, status__in=['completed', 'delivered']).first()
    if not order:
        raise Http404
    pdf = LabReportPDF(order, order.clinic, is_online_copy=True)
    return pdf.as_download_response() if request.GET.get('download') else pdf.as_response()


@patient_login_required
def view_invoice(request, pk):
    from django.http import Http404
    from apps.billing.models import Invoice
    from apps.core.services.pdf_service import BillingInvoicePDF

    invoice = Invoice.objects.filter(pk=pk, patient=request.portal_patient).first()
    if not invoice:
        raise Http404
    pdf = BillingInvoicePDF(invoice, invoice.clinic)
    return pdf.as_download_response() if request.GET.get('download') else pdf.as_response()
