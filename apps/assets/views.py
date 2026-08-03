from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count
from apps.core.decorators import role_required
from apps.core.models import AuditLog
from .models import Asset, AssetCategory, AssetServiceLog


@role_required('accountant', 'hr_manager', feature_flag='is_assets_enabled')
def dashboard(request):
    clinic = request.clinic
    assets = Asset.objects.filter(clinic=clinic)
    total_book_value = sum((a.current_book_value for a in assets), start=0)
    overdue_services = AssetServiceLog.objects.filter(
        clinic=clinic, next_service_due__lt=timezone.now().date()
    ).select_related('asset')

    context = {
        'total_assets': assets.count(),
        'in_use': assets.filter(status='in_use').count(),
        'under_maintenance': assets.filter(status='under_maintenance').count(),
        'total_book_value': total_book_value,
        'overdue_services': overdue_services,
        'by_category': assets.values('category__name').annotate(count=Count('id')).order_by('-count'),
    }
    return render(request, 'assets/dashboard.html', context)


@role_required('accountant', 'hr_manager', feature_flag='is_assets_enabled')
def asset_list(request):
    assets = Asset.objects.filter(clinic=request.clinic).select_related('category')
    status = request.GET.get('status')
    if status:
        assets = assets.filter(status=status)
    return render(request, 'assets/asset_list.html', {'assets': assets, 'status_filter': status})


@role_required('accountant', 'hr_manager', feature_flag='is_assets_enabled')
def asset_create(request):
    categories = AssetCategory.objects.filter(clinic=request.clinic)
    if request.method == 'POST':
        category = get_object_or_404(AssetCategory, pk=request.POST.get('category'), clinic=request.clinic)
        asset = Asset.objects.create(
            clinic=request.clinic,
            created_by=request.user,
            category=category,
            name=request.POST.get('name'),
            asset_tag=request.POST.get('asset_tag'),
            serial_number=request.POST.get('serial_number', ''),
            location=request.POST.get('location', ''),
            purchase_date=request.POST.get('purchase_date'),
            purchase_cost=request.POST.get('purchase_cost') or 0,
            salvage_value=request.POST.get('salvage_value') or 0,
            useful_life_years=request.POST.get('useful_life_years') or category.default_useful_life_years,
            vendor=request.POST.get('vendor', ''),
            warranty_expires=request.POST.get('warranty_expires') or None,
            notes=request.POST.get('notes', ''),
        )
        AuditLog.log(f'Asset registered: {asset.asset_tag}', user=request.user, clinic=request.clinic,
                     model_name='Asset', object_id=asset.pk, request=request)
        messages.success(request, f'Asset "{asset.name}" registered.')
        return redirect('assets:asset_detail', pk=asset.pk)
    return render(request, 'assets/asset_form.html', {'categories': categories})


@role_required('accountant', 'hr_manager', feature_flag='is_assets_enabled')
def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk, clinic=request.clinic)
    service_logs = asset.service_logs.all()
    return render(request, 'assets/asset_detail.html', {'asset': asset, 'service_logs': service_logs})


@role_required('accountant', 'hr_manager', feature_flag='is_assets_enabled')
def service_log_create(request, asset_pk):
    asset = get_object_or_404(Asset, pk=asset_pk, clinic=request.clinic)
    if request.method == 'POST':
        log = AssetServiceLog.objects.create(
            clinic=request.clinic,
            created_by=request.user,
            asset=asset,
            service_type=request.POST.get('service_type', 'routine'),
            service_date=request.POST.get('service_date'),
            performed_by=request.POST.get('performed_by', ''),
            cost=request.POST.get('cost') or 0,
            description=request.POST.get('description', ''),
            next_service_due=request.POST.get('next_service_due') or None,
        )
        if log.service_type == 'repair':
            asset.status = 'in_use'
            asset.save(update_fields=['status'])
        AuditLog.log(f'Service logged for asset {asset.asset_tag}', user=request.user, clinic=request.clinic,
                     model_name='AssetServiceLog', object_id=log.pk, request=request)
        messages.success(request, 'Service log added.')
        return redirect('assets:asset_detail', pk=asset.pk)
    return render(request, 'assets/service_log_form.html', {'asset': asset})
