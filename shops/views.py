import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Brand, Category, Product, ProductVariant

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


@login_required
def seller_dashboard(request):
    shop = get_object_or_404(Shop, owner=request.user)
    products = shop.products.select_related('brand', 'category').order_by('-created_at')
    return render(request, 'shops/seller_dashboard.html', {'shop': shop, 'products': products})


@login_required
def seller_product_form(request, product_id=None):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    product = get_object_or_404(Product, pk=product_id, shop=shop) if product_id else None
    brands = Brand.objects.order_by('name')
    categories = Category.objects.order_by('name')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        sizes = request.POST.get('available_sizes', '').strip()
        try:
            price = Decimal(request.POST.get('price', ''))
            stock = int(request.POST.get('stock', '0'))
            discount_text = request.POST.get('discount_price', '').strip()
            discount_price = Decimal(discount_text) if discount_text else None
        except (InvalidOperation, TypeError, ValueError):
            price, stock, discount_price = None, -1, None
        brand = Brand.objects.filter(pk=request.POST.get('brand')).first()
        category = Category.objects.filter(pk=request.POST.get('category')).first()
        image = request.FILES.get('image')
        if not name or not description or not sizes or not brand or not category or price is None or price <= 0 or stock < 0:
            messages.error(request, 'Complete the product fields with a valid positive price and stock quantity.')
        elif discount_price is not None and (discount_price <= 0 or discount_price > price):
            messages.error(request, 'The sale price must be positive and no higher than the regular price.')
        elif not product and not image:
            messages.error(request, 'Add a product photo before publishing the product.')
        else:
            if product is None:
                product = Product(shop=shop)
            product.name = name
            product.description = description
            product.brand = brand
            product.category = category
            product.gender = request.POST.get('gender', 'unisex')
            product.price = price
            product.discount_price = discount_price
            product.available_sizes = sizes
            product.is_active = request.POST.get('is_active') == 'on'
            if not product.pk or not product.variants.exists():
                product.stock = stock
            if image:
                product.image = image
            product.save()
            messages.success(request, 'Product listing saved.')
            return redirect('seller_dashboard')
    return render(request, 'shops/seller_product_form.html', {
        'shop': shop,
        'product': product,
        'brands': brands,
        'categories': categories,
        'gender_choices': Product.GENDER_CHOICES,
        'has_variants': product.variants.exists() if product else False,
    })


@login_required
def seller_delete_product(request, product_id):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    product = get_object_or_404(Product, pk=product_id, shop=shop)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Your product listing was removed.')
    return redirect('seller_dashboard')


@login_required
def seller_manage_variants(request, product_id):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    product = get_object_or_404(Product, pk=product_id, shop=shop)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            size = request.POST.get('size', '').strip()
            color = request.POST.get('color', '').strip()
            try:
                stock = int(request.POST.get('stock', '0'))
                price_override_text = request.POST.get('price_override', '').strip()
                price_override = Decimal(price_override_text) if price_override_text else None
            except (TypeError, ValueError, InvalidOperation):
                stock, price_override = -1, None
            if not size or not color or stock < 0 or (price_override is not None and price_override <= 0):
                messages.error(request, 'Enter a size, color, non-negative stock, and valid optional price.')
            elif product.variants.filter(size=size, color=color).exists():
                messages.error(request, 'This size and color variant already exists.')
            else:
                ProductVariant.objects.create(
                    product=product,
                    size=size,
                    color=color,
                    stock=stock,
                    price_override=price_override,
                )
                messages.success(request, 'Size and color stock saved.')
        elif action == 'remove':
            ProductVariant.objects.filter(pk=request.POST.get('variant_id'), product=product).delete()
            messages.success(request, 'Variant removed.')
        return redirect('seller_manage_variants', product_id=product.pk)
    return render(request, 'shops/seller_variants.html', {
        'shop': shop,
        'product': product,
        'variants': product.variants.order_by('size', 'color'),
    })
