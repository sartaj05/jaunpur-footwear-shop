from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.db.models import Avg
from django.db.models import Q
import re
from .models import Product, Brand, Category, ProductReview, WishlistItem


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

    search = request.GET.get('search')
    brand = request.GET.get('brand')
    category = request.GET.get('category')
    size = request.GET.get('size')
    pincode = request.GET.get('pincode', '').strip() or request.session.get('delivery_pincode', '')
    if not pincode and request.user.is_authenticated:
        pincode = getattr(getattr(request.user, 'customerprofile', None), 'pincode', '')

    if search:
        products = products.filter(name__icontains=search)

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

    for product in products:
        product.display_price = product.final_price(pincode=pincode)
        product.has_discount = product.display_price < product.price

    return render(request, 'products/product_list.html', {
        'products': products,
        'brands': brands,
        'categories': categories,
        'pincode': pincode,
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

    return render(request, 'products/product_detail.html', {
        'product': product,
        'sizes': sizes,
        'variants': variants,
        'reviews': reviews,
        'average_rating': average_rating,
        'pincode': pincode,
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
