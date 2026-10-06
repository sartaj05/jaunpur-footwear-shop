import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product

from .models import Shop, ShopCoverage


@login_required
def apply_for_shop(request):
    shop = Shop.objects.filter(owner=request.user).first()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', 'Jaunpur').strip() or 'Jaunpur'
        pincode = request.POST.get('pincode', '').strip()
        if not name or not address or not re.fullmatch(r'[1-9][0-9]{5}', pincode):
            messages.error(request, 'Enter a shop name, address, and valid six-digit PIN code.')
        elif shop and shop.status == 'approved':
            messages.error(request, 'Your shop is already approved. Contact support to change its details.')
        else:
            values = {
                'name': name,
                'phone': phone,
                'email': email,
                'address': address,
                'city': city,
                'district': 'Jaunpur',
                'pincode': pincode,
                'status': 'pending',
            }
            if shop:
                for field, value in values.items():
                    setattr(shop, field, value)
            else:
                shop = Shop(owner=request.user, **values)
            shop.slug = ''
            shop.save()
            messages.success(request, 'Your Jaunpur shop application was submitted for review.')
            return redirect('shop_application')
    return render(request, 'shops/apply.html', {'shop': shop})


def shop_directory(request):
    shops = Shop.objects.filter(status='approved').order_by('name')
    pincode = request.GET.get('pincode', '').strip()
    if re.fullmatch(r'[1-9][0-9]{5}', pincode):
        shops = shops.filter(coverage_areas__pincode=pincode, coverage_areas__is_active=True).distinct()
    else:
        pincode = ''
    return render(request, 'shops/directory.html', {'shops': shops, 'pincode': pincode})


def shop_page(request, slug):
    shop = get_object_or_404(Shop, slug=slug, status='approved')
    products = Product.objects.filter(shop=shop, is_active=True).select_related('brand', 'category')
    return render(request, 'shops/detail.html', {
        'shop': shop,
        'products': products,
        'coverage_areas': shop.coverage_areas.filter(is_active=True),
    })


@login_required
def manage_shop_coverage(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if request.method == 'POST':
        pincode = request.POST.get('pincode', '').strip()
        area_name = request.POST.get('area_name', '').strip()
        try:
            fee = Decimal(request.POST.get('delivery_fee', '50'))
            if fee < 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            fee = None
        if not re.fullmatch(r'[1-9][0-9]{5}', pincode) or fee is None:
            messages.error(request, 'Enter a valid six-digit PIN code and a delivery fee of zero or more.')
        else:
            ShopCoverage.objects.update_or_create(
                shop=shop,
                pincode=pincode,
                defaults={'area_name': area_name, 'delivery_fee': fee, 'is_active': True},
            )
            messages.success(request, 'Delivery coverage saved for this PIN code.')
            return redirect('manage_shop_coverage')
    return render(request, 'shops/coverage.html', {
        'shop': shop,
        'coverage_areas': shop.coverage_areas.all(),
    })


@login_required
def remove_shop_coverage(request, coverage_id):
    coverage = get_object_or_404(ShopCoverage, pk=coverage_id, shop__owner=request.user, shop__status='approved')
    if request.method == 'POST':
        coverage.delete()
        messages.success(request, 'Delivery coverage removed.')
    return redirect('manage_shop_coverage')
