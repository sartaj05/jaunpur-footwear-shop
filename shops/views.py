import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product

from .models import Shop


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
    return render(request, 'shops/directory.html', {'shops': shops})


def shop_page(request, slug):
    shop = get_object_or_404(Shop, slug=slug, status='approved')
    products = Product.objects.filter(shop=shop, is_active=True).select_related('brand', 'category')
    return render(request, 'shops/detail.html', {'shop': shop, 'products': products})
