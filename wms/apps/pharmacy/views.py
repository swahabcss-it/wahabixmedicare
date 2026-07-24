from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q as models_Q
from apps.core.decorators import role_required
from apps.core.models import AuditLog
from .models import Medicine, MedicineBatch, PharmacySale, PharmacySaleItem


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def dashboard(request):
    clinic = request.clinic
    today = timezone.now().date()
    medicines = Medicine.objects.filter(clinic=clinic)
    sales_today = PharmacySale.objects.filter(clinic=clinic, created_at__date=today)
    low_stock = medicines.filter(stock_quantity__lte=10)
    context = {
        'total_meds': medicines.count(),
        'low_stock_count': low_stock.count(),
        'sales_today': sales_today.count(),
        'revenue_today': sum(s.total for s in sales_today),
        'low_stock_items': low_stock.order_by('stock_quantity')[:8],
        'recent_sales': PharmacySale.objects.filter(clinic=clinic).order_by('-created_at')[:8],
    }
    return render(request, 'pharmacy/dashboard.html', context)


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def medicine_list(request):
    meds = Medicine.objects.filter(clinic=request.clinic).order_by('name')
    return render(request, 'pharmacy/medicine_list.html', {'medicines': meds})


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def medicine_create(request):
    if request.method == 'POST':
        expiry = request.POST.get('expiry_date') or None
        Medicine.objects.create(
            clinic=request.clinic,
            name=request.POST.get('name'),
            generic_name=request.POST.get('generic_name', ''),
            brand=request.POST.get('brand', ''),
            barcode=request.POST.get('barcode', ''),
            unit=request.POST.get('unit', 'tablet'),
            purchase_price=request.POST.get('purchase_price', 0),
            sale_price=request.POST.get('sale_price', 0),
            stock_quantity=request.POST.get('stock_quantity', 0),
            low_stock_alert=request.POST.get('low_stock_alert', 10),
            expiry_date=expiry,
            batch_number=request.POST.get('batch_number', ''),
            created_by=request.user,
        )
        messages.success(request, 'Medicine added to stock!')
        return redirect('pharmacy:medicine_list')
    return render(request, 'pharmacy/medicine_form.html', {'action': 'Add'})


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def medicine_edit(request, pk):
    med = get_object_or_404(Medicine, pk=pk, clinic=request.clinic)
    if request.method == 'POST':
        med.name = request.POST.get('name', med.name)
        med.generic_name = request.POST.get('generic_name', med.generic_name)
        med.brand = request.POST.get('brand', med.brand)
        med.barcode = request.POST.get('barcode', med.barcode)
        med.unit = request.POST.get('unit', med.unit)
        med.purchase_price = request.POST.get('purchase_price', med.purchase_price)
        med.sale_price = request.POST.get('sale_price', med.sale_price)
        med.stock_quantity = request.POST.get('stock_quantity', med.stock_quantity)
        med.low_stock_alert = request.POST.get('low_stock_alert', med.low_stock_alert)
        med.expiry_date = request.POST.get('expiry_date') or None
        med.batch_number = request.POST.get('batch_number', med.batch_number)
        med.save()
        messages.success(request, f'"{med.name}" updated!')
        return redirect('pharmacy:medicine_list')
    return render(request, 'pharmacy/medicine_form.html', {'action': 'Edit', 'medicine': med})


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def sale_list(request):
    sales = PharmacySale.objects.filter(clinic=request.clinic).order_by('-created_at')
    return render(request, 'pharmacy/sale_list.html', {'sales': sales})


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def sale_create(request):
    medicines = Medicine.objects.filter(clinic=request.clinic, stock_quantity__gt=0)
    if request.method == 'POST':
        med_ids = request.POST.getlist('med_id')
        quantities = request.POST.getlist('med_qty')
        if not any(i and q for i, q in zip(med_ids, quantities)):
            messages.error(request, 'Add at least one medicine to the sale.')
            return render(request, 'pharmacy/sale_form.html', {'medicines': medicines})
        today = timezone.now()
        inv_no = f"PH{today.strftime('%Y%m%d')}{PharmacySale.objects.filter(clinic=request.clinic).count()+1:04d}"
        with transaction.atomic():
            sale = PharmacySale.objects.create(
                clinic=request.clinic,
                invoice_number=inv_no,
                patient_name=request.POST.get('patient_name', ''),
                status='paid',
                created_by=request.user,
            )
            subtotal = 0
            for mid, qty_str in zip(med_ids, quantities):
                if not mid or not qty_str:
                    continue
                try:
                    med = Medicine.objects.get(pk=mid, clinic=request.clinic)
                    qty = int(qty_str)
                    if qty <= 0:
                        continue
                    item_sub = qty * med.sale_price
                    PharmacySaleItem.objects.create(sale=sale, medicine=med, quantity=qty, unit_price=med.sale_price, subtotal=item_sub)
                    med.deduct_fefo(qty)
                    subtotal += item_sub
                except (Medicine.DoesNotExist, ValueError) as e:
                    messages.warning(request, str(e))
                    continue
            discount = Decimal(str(request.POST.get('discount', 0) or 0))
            sale.subtotal = subtotal
            sale.discount = discount
            sale.total = max(Decimal('0'), subtotal - discount)
            sale.save()

        # 🟢 AUTO MODE — Autonomous General Ledger routing for pharmacy revenue
        try:
            from apps.billing.models import LedgerEntry
            LedgerEntry.objects.create(
                clinic=request.clinic, date=timezone.now().date(), account='cash_vault', entry_type='debit',
                amount=sale.total, reference=inv_no, description=f'Pharmacy sale — {sale.patient_name or "Walk-in"}',
            )
            LedgerEntry.objects.create(
                clinic=request.clinic, date=timezone.now().date(), account='pharmacy_revenue', entry_type='credit',
                amount=sale.total, reference=inv_no, description=f'Pharmacy revenue — {sale.patient_name or "Walk-in"}',
            )
        except Exception:
            pass
        AuditLog.log(f'Pharmacy sale {inv_no} — Rs.{sale.total}', user=request.user, clinic=request.clinic, request=request)
        messages.success(request, f'Sale saved! Invoice: {inv_no} — Total: Rs.{sale.total}')
        return redirect('pharmacy:sale_list')
    return render(request, 'pharmacy/sale_form.html', {'medicines': medicines})


# ─── SMART POS: search, barcode, token-cart-fetch ─────────────────────────────
@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def pos(request):
    """The 1-screen Smart Pharmacy POS — combines barcode scan, fast search,
    and token-based cart auto-fetch from the doctor's prescription."""
    return render(request, 'pharmacy/pos.html', {})


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def medicine_search_ajax(request):
    """🟠 MANUAL FAIL-SAFE — Fast-Search Autocomplete. Type first 2 letters."""
    q = (request.GET.get('q') or '').strip()
    results = []
    if len(q) >= 2:
        meds = Medicine.objects.filter(clinic=request.clinic).filter(
            models_Q(name__icontains=q) | models_Q(generic_name__icontains=q) | models_Q(brand__icontains=q)
        )[:10]
        for m in meds:
            results.append({'id': m.pk, 'name': m.name, 'brand': m.brand, 'price': str(m.sale_price), 'stock': m.total_stock, 'unit': m.get_unit_display()})
    return JsonResponse({'results': results})


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def medicine_scan_ajax(request):
    """🟢 AUTO MODE — Laser Gun Scanning. Barcode → instant cart-ready item."""
    barcode = (request.GET.get('barcode') or '').strip()
    if not barcode:
        return JsonResponse({'found': False})
    med = Medicine.objects.filter(clinic=request.clinic, barcode=barcode).first()
    if not med:
        return JsonResponse({'found': False})
    return JsonResponse({'found': True, 'id': med.pk, 'name': med.name, 'brand': med.brand,
                          'price': str(med.sale_price), 'stock': med.total_stock, 'unit': med.get_unit_display(),
                          'batch': med.batch_number, 'expiry': str(med.nearest_expiry or '')})


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def fetch_prescription_cart_ajax(request, token_pk):
    """🟢 AUTO MODE — Token-Based Cart Fetch. Scan patient token → doctor's
    prescription medicines auto-load into the POS cart, matched to stock."""
    from apps.reception.models import Token
    token = get_object_or_404(Token, pk=token_pk, clinic=request.clinic)
    rx = token.prescriptions.order_by('-visit_date').first()
    if not rx:
        return JsonResponse({'found': False, 'message': 'No prescription found for this token yet.'})
    items = []
    for pm in rx.medicines.all():
        med = _find_matching_medicine(request.clinic, pm.medicine_name)
        items.append({
            'medicine_name': pm.medicine_name,
            'dosage': pm.dosage,
            'frequency': pm.frequency,
            'duration': pm.duration,
            'matched': bool(med),
            'medicine_id': med.pk if med else None,
            'price': str(med.sale_price) if med else '0',
            'stock': med.total_stock if med else 0,
        })
    return JsonResponse({
        'found': True,
        'patient_name': token.patient.full_name,
        'patient_id': token.patient.patient_id,
        'rx_id': rx.pk,
        'items': items,
    })


def _find_matching_medicine(clinic, prescribed_name):
    """
    Matches a doctor's free-text prescription line against the pharmacy
    stock catalog. Tries progressively looser matches so real-world
    spelling/brand variance (e.g. "Panadol Extra" vs "Panadol", or a
    generic name instead of a brand name) still auto-loads into the POS
    cart instead of forcing manual add for near-misses.
    """
    name = prescribed_name.strip()
    if not name:
        return None
    # 1. Exact brand name match (case-insensitive) — the common case.
    med = Medicine.objects.filter(clinic=clinic, name__iexact=name).first()
    if med:
        return med
    # 2. Exact generic name match — doctor wrote the generic, not the brand.
    med = Medicine.objects.filter(clinic=clinic, generic_name__iexact=name).first()
    if med:
        return med
    # 3. Partial match either direction — handles "Panadol Extra" typed
    #    when stock has "Panadol", or vice versa.
    med = Medicine.objects.filter(clinic=clinic, name__icontains=name).first()
    if med:
        return med
    first_word = name.split()[0] if name.split() else name
    med = Medicine.objects.filter(clinic=clinic, name__icontains=first_word).first()
    if med:
        return med
    # 4. Generic name partial match as a last resort.
    med = Medicine.objects.filter(clinic=clinic, generic_name__icontains=first_word).first()
    return med


@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def batch_list(request, med_pk):
    med = get_object_or_404(Medicine, pk=med_pk, clinic=request.clinic)
    batches = med.batches.all().order_by('expiry_date')
    if request.method == 'POST':
        MedicineBatch.objects.create(
            clinic=request.clinic, medicine=med,
            batch_number=request.POST.get('batch_number', ''),
            quantity=request.POST.get('quantity', 0),
            purchase_price=request.POST.get('purchase_price', 0),
            expiry_date=request.POST.get('expiry_date'),
            created_by=request.user,
        )
        messages.success(request, f'Batch added for {med.name} — FEFO will auto-allocate by expiry.')
        return redirect('pharmacy:batch_list', med_pk=med.pk)
    return render(request, 'pharmacy/batch_list.html', {'medicine': med, 'batches': batches})


# ─── PDF ──────────────────────────────────────────────────────────────────────
@role_required('pharmacist', feature_flag='is_pharmacy_enabled')
def sale_pdf(request, pk):
    """Generate pharmacy invoice PDF — inline or download."""
    from apps.core.services.pdf_service import PharmacyInvoicePDF
    sale = get_object_or_404(PharmacySale, pk=pk, clinic=request.clinic)
    pdf = PharmacyInvoicePDF(sale, request.clinic, generated_by=request.user.get_full_name())
    if request.GET.get('download'):
        return pdf.as_download_response()
    return pdf.as_response()
