from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from apps.core.decorators import role_required
from apps.core.models import AuditLog
from .models import Patient, Token


@role_required('receptionist', feature_flag='is_reception_enabled')
def dashboard(request):
    clinic = request.clinic
    today = timezone.now().date()
    patients = Patient.objects.filter(clinic=clinic)
    tokens_today = Token.objects.filter(clinic=clinic, visit_date=today)
    from apps.billing.models import Invoice
    pending_lab_count = Invoice.objects.filter(clinic=clinic, lab_order__isnull=False, status__in=['draft', 'partial']).count()
    context = {
        'total_patients': patients.count(),
        'tokens_today': tokens_today.count(),
        'waiting': tokens_today.filter(status='waiting').count(),
        'done': tokens_today.filter(status='done').count(),
        'recent_tokens': tokens_today.select_related('patient').order_by('token_number')[:15],
        'pending_lab_count': pending_lab_count,
    }
    return render(request, 'reception/dashboard.html', context)

@role_required("receptionist", feature_flag="is_reception_enabled")
def patient_list(request):
    clinic = request.clinic
    patients = Patient.objects.filter(clinic=clinic).order_by('-created_at')
    return render(request, 'reception/patient_list.html', {'patients': patients})

@role_required("receptionist", feature_flag="is_reception_enabled")
def patient_create(request):
    if request.method == 'POST':
        patient = Patient.objects.create(
            clinic=request.clinic,
            full_name=request.POST.get('full_name'),
            age=request.POST.get('age'),
            gender=request.POST.get('gender'),
            phone=request.POST.get('phone'),
            cnic=request.POST.get('cnic',''),
            blood_group=request.POST.get('blood_group',''),
            address=request.POST.get('address',''),
            email=request.POST.get('email',''),
            allergies=request.POST.get('allergies',''),
            created_by=request.user,
        )
        # Portal access is generated automatically at registration — the
        # patient walks out already able to log in and see their own
        # records, instead of Reception having to remember a separate step.
        portal_password = patient.generate_portal_password()
        AuditLog.log(f'Patient registered: {patient.full_name}', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Patient "{patient.full_name}" registered! ID: {patient.patient_id}')
        return render(request, 'reception/portal_access.html', {'patient': patient, 'new_password': portal_password})
    return render(request, 'reception/patient_form.html', {'action': 'Register'})

@role_required("receptionist", feature_flag="is_reception_enabled")
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk, clinic=request.clinic)
    tokens = Token.objects.filter(patient=patient).order_by('-visit_date')[:10]
    return render(request, 'reception/patient_detail.html', {'patient': patient, 'tokens': tokens})

@role_required("receptionist", feature_flag="is_reception_enabled")
def generate_portal_access(request, pk):
    """
    Generates (or resets) a patient's Patient-Portal password and shows it
    ONCE on screen for Reception to write down / print for the patient —
    exactly like handing over a "Username / Password" slip. The plain
    password is never stored — only its hash — so if it's lost, Reception
    just generates a new one here.
    """
    patient = get_object_or_404(Patient, pk=pk, clinic=request.clinic)
    new_password = None
    if request.method == 'POST':
        new_password = patient.generate_portal_password()
        AuditLog.log(f'Patient portal access (re)generated for {patient.full_name}',
                     user=request.user, clinic=request.clinic, request=request)
    return render(request, 'reception/portal_access.html', {'patient': patient, 'new_password': new_password})

@role_required("receptionist", feature_flag="is_reception_enabled")
def token_list(request):
    today = timezone.now().date()
    tokens = Token.objects.filter(clinic=request.clinic, visit_date=today).select_related('patient').order_by('token_number')
    return render(request, 'reception/token_list.html', {'tokens': tokens, 'today': today})

@role_required("receptionist", feature_flag="is_reception_enabled")
def patient_search_ajax(request):
    """
    MANUAL FAIL-SAFE — Smart Selection Grid.
    Counter-speed patient lookup: staff types phone or first 2 letters of
    name, we return ready-made "smart cards" the receptionist can click —
    zero typing beyond the search term, no dropdown scrolling.
    Used when the biometric/ID-card auto-extraction path is unavailable.
    """
    q = (request.GET.get('q') or '').strip()
    results = []
    if len(q) >= 2:
        from django.db.models import Q
        patients = Patient.objects.filter(clinic=request.clinic).filter(
            Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(cnic__icontains=q)
        ).order_by('full_name')[:8]
        for p in patients:
            results.append({
                'id': p.pk,
                'name': p.full_name,
                'patient_id': p.patient_id,
                'phone': p.phone,
                'age': p.age,
                'gender': p.get_gender_display(),
                'blood_group': p.blood_group or '—',
                'allergies': p.allergies or '',
            })
    return JsonResponse({'results': results})


@role_required("receptionist", feature_flag="is_reception_enabled")
def token_create(request):
    if request.method == 'POST':
        patient = get_object_or_404(Patient, pk=request.POST.get('patient_id'), clinic=request.clinic)
        fee = request.POST.get('fee_paid') or 0
        try:
            fee = float(fee)
        except (TypeError, ValueError):
            fee = 0

        # Payment is mandatory — a token is the invoice, so there is no
        # such thing as a token without a payment behind it. This also
        # keeps Accounts fully reconciled: every token that exists has a
        # matching invoice, with no exceptions to explain later.
        if fee <= 0:
            messages.error(request, 'A consultation fee must be collected before a token can be issued. Enter the amount received.')
            patients = Patient.objects.filter(clinic=request.clinic).order_by('full_name')
            return render(request, 'reception/token_form.html', {
                'patients': patients, 'selected_patient_id': patient.pk,
            })

        today = timezone.now().date()
        last = Token.objects.filter(clinic=request.clinic, visit_date=today).order_by('-token_number').first()
        number = (last.token_number + 1) if last else 1

        token = Token.objects.create(
            clinic=request.clinic,
            patient=patient,
            token_number=number,
            blood_pressure=request.POST.get('blood_pressure',''),
            temperature=request.POST.get('temperature',''),
            weight=request.POST.get('weight',''),
            pulse=request.POST.get('pulse',''),
            fee_paid=fee,
            notes=request.POST.get('notes',''),
            created_by=request.user,
        )

        # The token IS the invoice — payment is already confirmed above,
        # so an Invoice always gets created and posted to the ledger here.
        if True:
            from apps.billing.models import Invoice, InvoiceItem
            from apps.billing.views import _autonomous_ledger_route

            count = Invoice.objects.filter(clinic=request.clinic).count() + 1
            inv_no = f"INV{timezone.now().strftime('%Y%m')}{count:04d}"
            invoice = Invoice.objects.create(
                clinic=request.clinic,
                patient=patient,
                invoice_number=inv_no,
                subtotal=fee,
                total=fee,
                amount_paid=fee,
                status='paid',
                notes=f'Auto-generated at reception — Token #{number}',
                created_by=request.user,
            )
            InvoiceItem.objects.create(
                invoice=invoice,
                description=f'Consultation / Token Fee — Token #{number}',
                quantity=1,
                unit_price=fee,
                subtotal=fee,
            )
            _autonomous_ledger_route(invoice, revenue_account='consultation_revenue')
            token.invoice = invoice
            token.save(update_fields=['invoice'])
            AuditLog.log(f'Reception invoice auto-created: {inv_no} (Token #{number})',
                         user=request.user, clinic=request.clinic,
                         model_name='Invoice', object_id=invoice.pk, request=request)
            messages.success(request, f'Token #{token.token_number} issued & Invoice {inv_no} created — Rs.{fee} collected.')

        from apps.core.services.notifications import notify_token_issued
        notify_token_issued(token)

        return redirect('reception:token_print', pk=token.pk)
    patients = Patient.objects.filter(clinic=request.clinic).order_by('full_name')
    return render(request, 'reception/token_form.html', {
        'patients': patients, 'selected_patient_id': request.GET.get('patient', ''),
    })


@role_required("receptionist", feature_flag="is_reception_enabled")
def token_print(request, pk):
    """
    The single printable slip: token number + invoice/receipt in one —
    'token is also the invoice'. Patient Portal login (ID + password) is
    always printed here too — a fresh password is generated on every
    print so whatever's on the physical slip is guaranteed to actually
    work, even on a reprint days later. There's no other reliable way to
    show a plain-text password on demand since only its hash is stored
    afterward — regenerating it here is the trade-off for that guarantee.
    """
    token = get_object_or_404(Token.objects.select_related('patient', 'invoice'), pk=pk, clinic=request.clinic)
    portal_password = token.patient.generate_portal_password()
    return render(request, 'reception/token_print.html', {
        'token': token, 'clinic': request.clinic, 'portal_password': portal_password,
    })


@role_required("receptionist", feature_flag="is_reception_enabled")
def pending_lab_payments(request):
    """
    Every lab order a doctor creates auto-generates an unpaid invoice
    (see apps.doctor.views.prescription_create). This is where Reception
    collects that payment from the patient — on their way to the lab, or
    on their way out. Also shows recently collected ones so the invoice
    can still be found & downloaded/printed after payment.
    """
    from apps.billing.models import Invoice
    pending = (
        Invoice.objects.filter(clinic=request.clinic, lab_order__isnull=False, status__in=['draft', 'partial'])
        .select_related('patient', 'lab_order')
        .order_by('-created_at')
    )
    recently_collected = (
        Invoice.objects.filter(clinic=request.clinic, lab_order__isnull=False, status='paid')
        .select_related('patient', 'lab_order')
        .order_by('-created_at')[:20]
    )
    return render(request, 'reception/pending_lab_payments.html', {
        'pending_invoices': pending, 'recently_collected': recently_collected,
    })


@role_required("receptionist", feature_flag="is_reception_enabled")
def collect_lab_payment(request, invoice_pk):
    from apps.billing.models import Invoice
    from apps.billing.views import _autonomous_ledger_route

    invoice = get_object_or_404(Invoice, pk=invoice_pk, clinic=request.clinic, lab_order__isnull=False)
    if request.method == 'POST':
        invoice.amount_paid = invoice.total
        invoice.status = 'paid'
        invoice.save(update_fields=['amount_paid', 'status'])
        _autonomous_ledger_route(invoice, revenue_account='lab_revenue')
        AuditLog.log(f'Lab payment collected: {invoice.invoice_number} (Rs.{invoice.total})',
                     user=request.user, clinic=request.clinic,
                     model_name='Invoice', object_id=invoice.pk, request=request)
        messages.success(request, f'Payment collected — Invoice {invoice.invoice_number} (Rs.{invoice.total}).')
    return redirect('reception:pending_lab_payments')
