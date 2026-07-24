from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from apps.core.decorators import role_required
from apps.core.models import AuditLog
from apps.reception.models import Patient
from .models import Invoice, InvoiceItem, InsurancePanel, InsuranceClaim, LedgerEntry


def _autonomous_ledger_route(invoice, revenue_account='consultation_revenue'):
    """
    🟢 AUTO MODE — Autonomous General Ledger.
    Transaction Cleared → Auto Matrix Routing →
      Debit: Central Operating Cash Vault
      Credit: Departmental Revenue Sub-Ledger Row
    Idempotent via Invoice.is_ledgered so re-visiting an invoice never
    double-posts.
    """
    if invoice.is_ledgered or invoice.status != 'paid':
        return
    today = timezone.now().date()
    LedgerEntry.objects.create(
        clinic=invoice.clinic, date=today, account='cash_vault', entry_type='debit',
        amount=invoice.amount_paid, reference=invoice.invoice_number,
        description=f'Payment received — {invoice.patient.full_name}',
    )
    LedgerEntry.objects.create(
        clinic=invoice.clinic, date=today, account=revenue_account, entry_type='credit',
        amount=invoice.amount_paid, reference=invoice.invoice_number,
        description=f'Revenue recognized — {invoice.patient.full_name}',
    )
    invoice.is_ledgered = True
    invoice.save(update_fields=['is_ledgered'])


@role_required('accountant', feature_flag='is_billing_enabled')
def dashboard(request):
    clinic = request.clinic
    today = timezone.now().date()
    invoices = Invoice.objects.filter(clinic=clinic)
    invoices_today = invoices.filter(created_at__date=today)
    context = {
        'total_invoices': invoices.count(),
        'paid_today': invoices_today.filter(status='paid').count(),
        'pending': invoices.filter(status__in=['draft', 'partial']).count(),
        'revenue_today': sum(i.amount_paid for i in invoices_today.filter(status='paid')),
        'recent_invoices': invoices.select_related('patient').order_by('-created_at')[:10],
    }
    return render(request, 'billing/dashboard.html', context)


@role_required('accountant', feature_flag='is_billing_enabled', permission_flag='can_access_billing')
def invoice_list(request):
    invoices = Invoice.objects.filter(clinic=request.clinic).select_related('patient').order_by('-created_at')
    return render(request, 'billing/invoice_list.html', {'invoices': invoices})


@role_required('accountant', feature_flag='is_billing_enabled', permission_flag='can_access_billing')
def invoice_create(request):
    from apps.licensing.helpers import is_billing_restricted
    patients = Patient.objects.filter(clinic=request.clinic).order_by('full_name')
    panels = InsurancePanel.objects.filter(clinic=request.clinic, is_active=True)
    if is_billing_restricted(request):
        messages.error(
            request,
            '⚠️ New invoices are paused — your clinic subscription has expired. '
            'All patient, lab, doctor and pharmacy records remain fully accessible. '
            'Contact Wahabix Support to renew and resume billing.'
        )
        return redirect('billing:invoice_list')
    if request.method == 'POST':
        patient = get_object_or_404(Patient, pk=request.POST.get('patient_id'), clinic=request.clinic)
        count = Invoice.objects.filter(clinic=request.clinic).count() + 1
        inv_no = f"INV{timezone.now().strftime('%Y%m')}{count:04d}"
        descs = request.POST.getlist('item_desc')
        qtys = request.POST.getlist('item_qty')
        prices = request.POST.getlist('item_price')
        subtotal = 0
        items_data = []
        for desc, qty_s, price_s in zip(descs, qtys, prices):
            if desc.strip():
                qty = int(qty_s or 1)
                price = float(price_s or 0)
                item_sub = qty * price
                subtotal += item_sub
                items_data.append((desc, qty, price, item_sub))
        discount = float(request.POST.get('discount', 0) or 0)
        tax_pct = float(request.POST.get('tax_pct', 0) or 0)
        tax = round((subtotal - discount) * tax_pct / 100, 2)
        total = max(0, subtotal - discount + tax)
        amount_paid = float(request.POST.get('amount_paid', 0) or 0)
        status = 'paid' if amount_paid >= total else ('partial' if amount_paid > 0 else 'draft')
        panel_id = request.POST.get('insurance_panel_id') or None
        inv = Invoice.objects.create(
            clinic=request.clinic, patient=patient,
            invoice_number=inv_no, subtotal=subtotal,
            discount=discount, tax=tax, total=total,
            amount_paid=amount_paid, status=status,
            insurance_panel_id=panel_id,
            notes=request.POST.get('notes', ''),
            created_by=request.user,
        )
        for desc, qty, price, item_sub in items_data:
            InvoiceItem.objects.create(invoice=inv, description=desc, quantity=qty, unit_price=price, subtotal=item_sub)

        # ── INSURANCE CLAIM SCRUBBING ────────────────────────────────────────
        claim_msg = ''
        if panel_id:
            panel = InsurancePanel.objects.get(pk=panel_id, clinic=request.clinic)
            patient_share = round(total * float(panel.co_payment_percent) / 100, 2)
            insurer_share = round(total - patient_share, 2)
            InsuranceClaim.objects.create(
                clinic=request.clinic, invoice=inv, panel=panel,
                patient_share=patient_share, insurer_share=insurer_share,
                created_by=request.user,
            )
            claim_msg = f' Insurance claim auto-scrubbed: Rs.{patient_share} patient / Rs.{insurer_share} {panel.name}.'

        # ── AUTONOMOUS GENERAL LEDGER ────────────────────────────────────────
        _autonomous_ledger_route(inv, revenue_account='consultation_revenue')

        AuditLog.log(f'Invoice {inv_no} created — Rs.{total}', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Invoice {inv_no} created! Total: Rs.{total}.{claim_msg}')
        return redirect('billing:invoice_list')
    return render(request, 'billing/invoice_form.html', {'patients': patients, 'panels': panels})


@role_required('accountant', feature_flag='is_billing_enabled', permission_flag='can_access_billing')
def invoice_detail(request, pk):
    inv = get_object_or_404(Invoice, pk=pk, clinic=request.clinic)
    items = inv.items.all()
    return render(request, 'billing/invoice_detail.html', {'invoice': inv, 'items': items})


# ─── LEDGER ────────────────────────────────────────────────────────────────────
@role_required('accountant', feature_flag='is_billing_enabled')
def ledger_report(request):
    entries = LedgerEntry.objects.filter(clinic=request.clinic).order_by('-date', '-created_at')
    account = request.GET.get('account')
    if account:
        entries = entries.filter(account=account)
    total_debit = entries.filter(entry_type='debit').aggregate(t=Sum('amount'))['t'] or 0
    total_credit = entries.filter(entry_type='credit').aggregate(t=Sum('amount'))['t'] or 0
    return render(request, 'billing/ledger_report.html', {
        'entries': entries[:200], 'total_debit': total_debit, 'total_credit': total_credit,
        'accounts': LedgerEntry.ACCOUNTS, 'selected_account': account,
    })


# ─── INSURANCE PANELS ────────────────────────────────────────────────────────
@role_required('accountant', feature_flag='is_billing_enabled')
def panel_list(request):
    panels = InsurancePanel.objects.filter(clinic=request.clinic)
    if request.method == 'POST':
        InsurancePanel.objects.create(
            clinic=request.clinic, name=request.POST.get('name'),
            co_payment_percent=request.POST.get('co_payment_percent', 20),
            contact_person=request.POST.get('contact_person', ''),
            contact_phone=request.POST.get('contact_phone', ''),
            created_by=request.user,
        )
        messages.success(request, 'Insurance panel added.')
        return redirect('billing:panel_list')
    return render(request, 'billing/panel_list.html', {'panels': panels})


# ─── INSURANCE CLAIMS — Batch Action Triggers ──────────────────────────────────
@role_required('accountant', feature_flag='is_billing_enabled')
def claim_list(request):
    claims = InsuranceClaim.objects.filter(clinic=request.clinic).select_related('invoice', 'panel', 'invoice__patient').order_by('-created_at')
    status = request.GET.get('status')
    panel_id = request.GET.get('panel')
    if status:
        claims = claims.filter(status=status)
    if panel_id:
        claims = claims.filter(panel_id=panel_id)
    panels = InsurancePanel.objects.filter(clinic=request.clinic)
    return render(request, 'billing/claim_list.html', {
        'claims': claims, 'panels': panels, 'selected_status': status, 'selected_panel': panel_id,
    })


@role_required('accountant', feature_flag='is_billing_enabled')
def claim_batch_approve(request):
    """
    🟠 MANUAL FAIL-SAFE — Batch Action Triggers.
    Accountant multi-selects filtered claims and clears a whole month of
    panel claims with a single click, instead of approving one by one.
    """
    if request.method == 'POST':
        claim_ids = request.POST.getlist('claim_ids')
        if not claim_ids:
            messages.warning(request, 'No claims selected.')
            return redirect('billing:claim_list')
        import uuid
        batch_ref = f"BATCH-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        updated = InsuranceClaim.objects.filter(pk__in=claim_ids, clinic=request.clinic, status='pending').update(
            status='submitted', batch_ref=batch_ref, submitted_at=timezone.now(),
        )
        AuditLog.log(f'Batch-submitted {updated} insurance claims ({batch_ref})', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'✅ {updated} claims batch-approved & submitted under {batch_ref}.')
    return redirect('billing:claim_list')


# ─── PDF ──────────────────────────────────────────────────────────────────────
# ─── PDF ──────────────────────────────────────────────────────────────────────
@role_required('accountant', feature_flag='is_billing_enabled')
def ledger_pdf(request):
    """Accounts / General Ledger PDF export — inline view or ?download=1."""
    from apps.core.services.pdf_service import LedgerReportPDF
    entries = LedgerEntry.objects.filter(clinic=request.clinic).order_by('-date', '-created_at')
    account = request.GET.get('account')
    account_label = None
    if account:
        entries = entries.filter(account=account)
        account_label = dict(LedgerEntry.ACCOUNTS).get(account, account)
    total_debit = entries.filter(entry_type='debit').aggregate(t=Sum('amount'))['t'] or 0
    total_credit = entries.filter(entry_type='credit').aggregate(t=Sum('amount'))['t'] or 0
    pdf = LedgerReportPDF(entries[:500], request.clinic, generated_by=request.user.get_full_name(),
                           total_debit=total_debit, total_credit=total_credit, account_filter=account_label)
    if request.GET.get('download'):
        return pdf.as_download_response()
    return pdf.as_response()


@role_required('accountant', feature_flag='is_billing_enabled', permission_flag='can_access_billing')
def invoice_pdf(request, pk):
    """Generate billing invoice PDF — inline view or ?download=1 for file download."""
    from apps.core.services.pdf_service import BillingInvoicePDF
    inv = get_object_or_404(Invoice, pk=pk, clinic=request.clinic)
    pdf = BillingInvoicePDF(inv, request.clinic, generated_by=request.user.get_full_name())
    if request.GET.get('download'):
        return pdf.as_download_response()
    return pdf.as_response()
