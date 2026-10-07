from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.db.models import Avg
from django.db.models import Q
from django.urls import reverse
import json
import re
from .models import Product, Brand, Category, ProductReview, WishlistItem
from .search import product_search_query
from shops.inventory import local_available_stock


def home(request):
    featured_products = Product.objects.filter(is_active=True, is_featured=True).filter(
        Q(shop__isnull=True) | Q(shop__status='approved')
    )[:8]
    categories = Category.objects.all()
    brands = Brand.objects.all()
    pincode = request.session.get('delivery_pincode', '')
    if not pincode and request.user.is_authenticated:
        pincode = getattr(getattr(request.user, 'customerprofile', None), 'pincode', '')
    for product in featured_products:
        product.display_price = product.final_price(pincode=pincode)
        product.has_discount = product.display_price < product.price

    return render(request, 'products/home.html', {
        'featured_products': featured_products,
        'categories': categories,
        'brands': brands,
    })


def product_list(request):
    products = Product.objects.filter(is_active=True).filter(
        Q(shop__isnull=True) | Q(shop__status='approved')
    )
    brands = Brand.objects.all()
    categories = Category.objects.all()

    search = request.GET.get('search', '').strip()
    brand = request.GET.get('brand')
    category = request.GET.get('category')
    size = request.GET.get('size')
    in_stock = request.GET.get('in_stock') == '1'
    pincode = request.GET.get('pincode', '').strip() or request.session.get('delivery_pincode', '')
    if not pincode and request.user.is_authenticated:
        pincode = getattr(getattr(request.user, 'customerprofile', None), 'pincode', '')

    if search:
        products = products.filter(product_search_query(search))

    if brand:
        products = products.filter(brand_id=brand)

    if category:
        products = products.filter(category_id=category)

    if size:
        products = products.filter(available_sizes__icontains=size)

    if re.fullmatch(r'[1-9][0-9]{5}', pincode):
        request.session['delivery_pincode'] = pincode
        products = products.filter(
            Q(shop__isnull=True)
            | Q(shop__coverage_areas__pincode=pincode, shop__coverage_areas__is_active=True)
        ).distinct()
    else:
        pincode = ''

    if in_stock:
        available_products = []
        for product in products.prefetch_related('variants'):
            active_variants = [variant for variant in product.variants.all() if variant.is_active]
            stock_owners = active_variants or [product]
            if any(local_available_stock(stock_owner) > 0 for stock_owner in stock_owners):
                available_products.append(product)
        products = available_products

    for product in products:
        product.display_price = product.final_price(pincode=pincode)
        product.has_discount = product.display_price < product.price

    return render(request, 'products/product_list.html', {
        'products': products,
        'brands': brands,
        'categories': categories,
        'pincode': pincode,
        'search': search,
        'in_stock': in_stock,
    })


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.filter(Q(shop__isnull=True) | Q(shop__status='approved')),
        pk=pk,
        is_active=True,
    )
    sizes = [s.strip() for s in product.available_sizes.split(',')]
    variants = product.variants.filter(is_active=True)
    pincode = request.GET.get('pincode', '').strip() or request.session.get('delivery_pincode', '')
    if not pincode and request.user.is_authenticated:
        pincode = getattr(getattr(request.user, 'customerprofile', None), 'pincode', '')
    if re.fullmatch(r'[1-9][0-9]{5}', pincode or ''):
        request.session['delivery_pincode'] = pincode
    else:
        pincode = ''
    product.display_price = product.final_price(pincode=pincode)
    product.has_discount = product.display_price < product.price
    for variant in variants:
        variant.display_price = variant.final_price(pincode=pincode)
    reviews = product.reviews.select_related('user')
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    active_variants = [variant for variant in variants if variant.is_active]
    stock_owners = active_variants or [product]
    available_stock = sum(local_available_stock(owner) for owner in stock_owners)
    canonical_url = request.build_absolute_uri(reverse('product_detail', kwargs={'pk': product.pk}))
    product_description = product.description_hi if request.session.get('site_language') == 'hi' and product.description_hi else product.description
    schema_data = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': product.name_hi if request.session.get('site_language') == 'hi' and product.name_hi else product.name,
        'description': product_description,
        'image': request.build_absolute_uri(product.image.url) if product.image else '',
        'sku': product.seller_sku or str(product.pk),
        'brand': {'@type': 'Brand', 'name': product.brand.name},
        'offers': {
            '@type': 'Offer',
            'url': canonical_url,
            'priceCurrency': 'INR',
            'price': str(product.display_price),
            'availability': 'https://schema.org/InStock' if available_stock else 'https://schema.org/OutOfStock',
            'itemCondition': 'https://schema.org/NewCondition',
        },
    }
    if average_rating:
        schema_data['aggregateRating'] = {'@type': 'AggregateRating', 'ratingValue': round(average_rating, 1), 'reviewCount': reviews.count()}
    structured_data = json.dumps(schema_data, ensure_ascii=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')

    return render(request, 'products/product_detail.html', {
        'product': product,
        'sizes': sizes,
        'variants': variants,
        'reviews': reviews,
        'average_rating': average_rating,
        'pincode': pincode,
        'canonical_url': canonical_url,
        'seo_description': product_description[:300],
        'structured_data': structured_data,
        'is_wishlisted': (
            request.user.is_authenticated
            and WishlistItem.objects.filter(user=request.user, product=product).exists()
        ),
    })


@login_required
def wishlist_view(request):
    items = WishlistItem.objects.filter(user=request.user).select_related(
        'product', 'product__brand', 'product__category'
    )
    pincode = request.session.get('delivery_pincode', '')
    if not pincode and request.user.is_authenticated:
        pincode = getattr(getattr(request.user, 'customerprofile', None), 'pincode', '')
    for item in items:
        item.product.display_price = item.product.final_price(pincode=pincode)
    return render(request, 'products/wishlist.html', {'wishlist_items': items})


@login_required
@require_POST
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    _, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, f'{product.name} was saved to your wishlist.')
    return redirect('product_detail', pk=product.pk)


@login_required
@require_POST
def remove_from_wishlist(request, product_id):
    WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
    messages.success(request, 'Product removed from your wishlist.')
    return redirect('wishlist')


@login_required
@require_POST
def submit_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    try:
        rating = int(request.POST.get('rating', ''))
    except (TypeError, ValueError):
        rating = 0
    body = request.POST.get('body', '').strip()
    title = request.POST.get('title', '').strip()
    if rating not in range(1, 6) or not body:
        messages.error(request, 'Choose a rating from 1 to 5 and write a review.')
    else:
        ProductReview.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={'rating': rating, 'title': title, 'body': body},
        )
        messages.success(request, 'Your product review was saved.')
    return redirect('product_detail', pk=product.pk)


def size_finder(request):
    suggested_size = None

    if request.method == 'POST':
        foot_length = float(request.POST.get('foot_length'))

        if foot_length <= 23:
            suggested_size = 'UK/India 5'
        elif foot_length <= 24:
            suggested_size = 'UK/India 6'
        elif foot_length <= 25:
            suggested_size = 'UK/India 7'
        elif foot_length <= 26:
            suggested_size = 'UK/India 8'
        elif foot_length <= 27:
            suggested_size = 'UK/India 9'
        elif foot_length <= 28:
            suggested_size = 'UK/India 10'
        else:
            suggested_size = 'UK/India 11+'

    return render(request, 'products/size_finder.html', {
        'suggested_size': suggested_size
    })
