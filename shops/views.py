import re
import csv
import io
import json
import os
import secrets
from decimal import Decimal, InvalidOperation
from datetime import time, timedelta, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core import signing
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Avg, Q, Sum
from django.db import transaction
from django.views.decorators.http import require_GET, require_POST
from urllib.parse import urlencode

from products.models import Brand, Category, Product, ProductVariant
from orders.models import Coupon, OrderTrackingEvent, ReturnRequest, SellerOrder
from orders.tasks import send_order_status_update_task
from footwear.task_dispatch import dispatch_background_task
from accounts.models import ReferralReward
from accounts.services import award_loyalty_for_order

from .models import MarketplaceChannelOrder, MarketplaceConnection, MarketplaceProductMapping, ONDCEnrollment, Shop, ShopCoverage, ShopFulfillmentSlot, ShopPromotion, ShopReview
from .inventory import local_available_stock, update_mapping_allocation
from .marketplace_auth import (
    MarketplaceAuthorizationError,
    encrypt_marketplace_token,
    exchange_amazon_code,
    exchange_flipkart_code,
    marketplace_encryption_is_configured,
)


def customer_delivery_pincode(request):
    if 'pincode' in request.GET:
        candidate = request.GET.get('pincode', '').strip()
    else:
        candidate = request.session.get('delivery_pincode', '')
        if not candidate and request.user.is_authenticated:
            candidate = getattr(getattr(request.user, 'customerprofile', None), 'pincode', '')
    if re.fullmatch(r'[1-9][0-9]{5}', candidate or ''):
        request.session['delivery_pincode'] = candidate
        return candidate
    return ''


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
    pincode = customer_delivery_pincode(request)
    for product in products:
        product.display_price = product.final_price(pincode=pincode)
        product.has_discount = product.display_price < product.price
    now = timezone.now()
    area_promotions = [
        promotion for promotion in shop.promotions.filter(is_active=True).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(expires_at__isnull=True) | Q(expires_at__gte=now),
        ).prefetch_related('products') if promotion.applies_to_pincode(pincode)
    ]
    return render(request, 'shops/detail.html', {
        'shop': shop,
        'products': products,
        'coverage_areas': shop.coverage_areas.filter(is_active=True),
        'fulfillment_slots': shop.fulfillment_slots.filter(is_active=True),
        'promotions': area_promotions,
        'pincode': pincode,
        'shop_review_average': shop.reviews.filter(is_visible=True).aggregate(value=Avg('rating'))['value'],
        'shop_review_count': shop.reviews.filter(is_visible=True).count(),
        'shop_reviews': shop.reviews.filter(is_visible=True).select_related('customer')[:10],
    })


@login_required
def review_shop(request, seller_order_id):
    seller_order = get_object_or_404(
        SellerOrder.objects.select_related('shop', 'order'),
        pk=seller_order_id,
        order__user=request.user,
        status='delivered',
        shop__isnull=False,
    )
    review = ShopReview.objects.filter(seller_order=seller_order, customer=request.user).first()
    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', '0'))
        except (TypeError, ValueError):
            rating = 0
        body = request.POST.get('body', '').strip()
        if rating not in range(1, 6) or len(body) > 1200:
            messages.error(request, 'Choose a rating from 1 to 5 and keep the review under 1,200 characters.')
        else:
            ShopReview.objects.update_or_create(
                seller_order=seller_order,
                defaults={
                    'shop': seller_order.shop,
                    'customer': request.user,
                    'rating': rating,
                    'body': body,
                    'is_visible': True,
                },
            )
            messages.success(request, 'Your verified-shop review was saved.')
            return redirect('shop_page', slug=seller_order.shop.slug)
    return render(request, 'shops/review.html', {'seller_order': seller_order, 'review': review})


@login_required
def manage_shop_coverage(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if request.method == 'POST':
        pincode = request.POST.get('pincode', '').strip()
        area_name = request.POST.get('area_name', '').strip()
        try:
            min_days = int(request.POST.get('min_delivery_days', '1'))
            max_days = int(request.POST.get('max_delivery_days', '3'))
            if min_days < 0 or max_days < min_days or max_days > 30:
                raise ValueError
        except (TypeError, ValueError):
            min_days, max_days = None, None
        try:
            fee = Decimal(request.POST.get('delivery_fee', '50'))
            if fee < 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            fee = None
        if not re.fullmatch(r'[1-9][0-9]{5}', pincode) or fee is None or min_days is None:
            messages.error(request, 'Enter a valid six-digit PIN code, delivery fee, and ETA range from 0 to 30 days.')
        else:
            ShopCoverage.objects.update_or_create(
                shop=shop,
                pincode=pincode,
                defaults={
                    'area_name': area_name,
                    'delivery_fee': fee,
                    'min_delivery_days': min_days,
                    'max_delivery_days': max_days,
                    'is_active': True,
                },
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
def manage_fulfillment_slots(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if request.method == 'POST':
        mode = request.POST.get('mode')
        try:
            weekday = int(request.POST.get('weekday', '-1'))
            start_time = time.fromisoformat(request.POST.get('start_time', ''))
            end_time = time.fromisoformat(request.POST.get('end_time', ''))
            max_orders = int(request.POST.get('max_orders', '20'))
        except (TypeError, ValueError):
            weekday, start_time, end_time, max_orders = -1, None, None, 0
        if mode not in ('delivery', 'pickup') or weekday not in range(7) or not start_time or not end_time or end_time <= start_time or max_orders < 1:
            messages.error(request, 'Choose a mode, weekday, valid opening hours, and capacity of at least one.')
        else:
            ShopFulfillmentSlot.objects.create(
                shop=shop,
                mode=mode,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
                max_orders=max_orders,
            )
            messages.success(request, 'Fulfillment time slot added.')
            return redirect('manage_fulfillment_slots')
    return render(request, 'shops/fulfillment_slots.html', {
        'shop': shop,
        'slots': shop.fulfillment_slots.all(),
        'weekdays': ShopFulfillmentSlot.WEEKDAY_CHOICES,
        'modes': ShopFulfillmentSlot.MODE_CHOICES,
    })


@login_required
def remove_fulfillment_slot(request, slot_id):
    slot = get_object_or_404(ShopFulfillmentSlot, pk=slot_id, shop__owner=request.user, shop__status='approved')
    if request.method == 'POST':
        if slot.seller_orders.exists():
            slot.is_active = False
            slot.save(update_fields=['is_active'])
            messages.success(request, 'The slot was closed for new orders; existing bookings keep their schedule.')
        else:
            slot.delete()
            messages.success(request, 'Fulfillment time slot removed.')
    return redirect('manage_fulfillment_slots')


@login_required
def seller_dashboard(request):
    shop = get_object_or_404(Shop, owner=request.user)
    products = shop.products.select_related('brand', 'category').order_by('-created_at')
    ready_payouts = shop.seller_orders.filter(status='delivered', payout_status='pending').filter(
        Q(order__payment_status='paid') | Q(order__payment_method='Cash on Delivery')
    ).exclude(order__status='cancelled')
    paid_payouts = shop.seller_orders.filter(payout_status='paid')
    return render(request, 'shops/seller_dashboard.html', {
        'shop': shop,
        'products': products,
        'pending_payout_total': ready_payouts.aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00'),
        'paid_payout_total': paid_payouts.aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00'),
        'shop_review_average': shop.reviews.filter(is_visible=True).aggregate(value=Avg('rating'))['value'],
        'shop_review_count': shop.reviews.filter(is_visible=True).count(),
    })


@login_required
def request_shop_verification(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if request.method == 'POST' and shop.verification_status != 'verified':
        if not shop.name or not shop.phone or not shop.address or not shop.pincode:
            messages.error(request, 'Complete your shop name, phone, address, and Jaunpur PIN code first.')
        else:
            shop.verification_status = 'pending'
            shop.verification_requested_at = timezone.now()
            shop.verification_note = ''
            shop.save(update_fields=['verification_status', 'verification_requested_at', 'verification_note', 'updated_at'])
            messages.success(request, 'Verification requested. Staff will review your shop details and contact you.')
    return redirect('seller_dashboard')


@login_required
def seller_orders(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    orders = shop.seller_orders.select_related('order', 'order__user').prefetch_related('items').order_by('-created_at')
    return render(request, 'shops/seller_orders.html', {
        'shop': shop,
        'seller_orders': orders,
        'status_choices': SellerOrder.STATUS_CHOICES,
    })


@login_required
def seller_return_requests(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    requests_for_shop = ReturnRequest.objects.filter(
        order_item__product__shop=shop,
    ).select_related('customer', 'order', 'order_item__product').order_by('-requested_at')
    error = ''
    if request.method == 'POST':
        try:
            request_id = int(request.POST.get('return_request_id', ''))
        except (TypeError, ValueError):
            request_id = 0
        return_request = requests_for_shop.filter(pk=request_id).first()
        status = request.POST.get('status', '')
        refund_status = request.POST.get('refund_status', '')
        refund_reference = request.POST.get('refund_reference', '').strip()
        pickup_text = request.POST.get('pickup_scheduled_at', '').strip()
        try:
            pickup_scheduled_at = _parse_local_datetime(pickup_text)
        except ValueError:
            pickup_scheduled_at = None
            error = 'Enter a valid pickup date and time.'
        if not error and (not return_request or status not in dict(ReturnRequest.STATUS_CHOICES) or refund_status not in dict(ReturnRequest.REFUND_STATUS_CHOICES)):
            error = 'Choose a valid request status and refund status.'
        if not error and refund_status == 'processed' and not refund_reference:
            error = 'Add the payment reference after you have actually sent the refund.'
        if error:
            messages.error(request, error)
        else:
            return_request.status = status
            return_request.refund_status = refund_status
            return_request.refund_reference = refund_reference
            return_request.pickup_scheduled_at = pickup_scheduled_at
            return_request.staff_note = request.POST.get('staff_note', '').strip()
            return_request.save(update_fields=[
                'status', 'refund_status', 'refund_reference', 'pickup_scheduled_at', 'staff_note', 'updated_at',
            ])
            messages.success(request, 'Return or exchange request updated. Refunds must be sent through the payment provider separately.')
            return redirect('seller_return_requests')
    return render(request, 'shops/seller_returns.html', {
        'shop': shop,
        'return_requests': requests_for_shop,
        'status_choices': ReturnRequest.STATUS_CHOICES,
        'refund_choices': ReturnRequest.REFUND_STATUS_CHOICES,
    })


@login_required
def seller_payout_ledger(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    seller_orders = shop.seller_orders.select_related('order').order_by('-created_at')
    return render(request, 'shops/payout_ledger.html', {'shop': shop, 'seller_orders': seller_orders})


@login_required
def update_seller_order_status(request, seller_order_id):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    seller_order = get_object_or_404(SellerOrder, pk=seller_order_id, shop=shop)
    if request.method == 'POST':
        status = request.POST.get('status')
        valid_statuses = dict(SellerOrder.STATUS_CHOICES)
        if seller_order.order.status == 'cancelled' or seller_order.order.payment_status == 'failed':
            messages.error(request, 'This checkout is no longer active.')
        elif seller_order.order.payment_status == 'pending':
            messages.error(request, 'Wait until online payment is confirmed before processing this order.')
        elif status not in valid_statuses:
            messages.error(request, 'Choose a valid order status.')
        elif status != seller_order.status:
            seller_order.status = status
            seller_order.save(update_fields=['status'])
            OrderTrackingEvent.objects.create(
                order=seller_order.order,
                status=status,
                note=f'{shop.name}: {request.POST.get("note", "").strip() or valid_statuses[status]}',
                created_by=request.user,
            )
            statuses = set(seller_order.order.seller_orders.values_list('status', flat=True))
            if len(statuses) == 1:
                overall_status = statuses.pop()
                seller_order.order.status = overall_status
                seller_order.order.save(update_fields=['status'])
                if overall_status == 'delivered':
                    award_loyalty_for_order(seller_order.order)
                    reward = ReferralReward.objects.filter(
                        referred_user_id=seller_order.order.user_id,
                        status='pending',
                    ).first()
                    if reward:
                        coupon_code = f'JP-REF-{reward.pk}'
                        Coupon.objects.create(
                            code=coupon_code,
                            discount_type='fixed',
                            discount_value=reward.amount,
                            usage_limit=1,
                            reserved_for_id=reward.referrer_id,
                            starts_at=timezone.now(),
                            expires_at=timezone.now() + timedelta(days=90),
                        )
                        reward.status = 'earned'
                        reward.reward_coupon_code = coupon_code
                        reward.earned_at = timezone.now()
                        reward.save(update_fields=['status', 'reward_coupon_code', 'earned_at'])
            transaction.on_commit(lambda order_id=seller_order.order_id: dispatch_background_task(send_order_status_update_task, order_id))
            messages.success(request, 'Your part of the customer order was updated.')
    return redirect('seller_orders')


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
            product.name_hi = request.POST.get('name_hi', '').strip()
            product.description = description
            product.description_hi = request.POST.get('description_hi', '').strip()
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
def import_seller_catalog(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    imported_count = 0
    errors = []
    if request.method == 'POST':
        catalog_file = request.FILES.get('catalog_file')
        image_files = request.FILES.getlist('images')
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        uploaded_images = {}
        total_upload_size = catalog_file.size if catalog_file else 0
        for image in image_files:
            total_upload_size += image.size
            filename = image.name.replace('\\', '/').split('/')[-1]
            if filename != image.name or os.path.splitext(filename)[1].lower() not in allowed_extensions:
                errors.append(f'{image.name}: use an image filename with JPG, PNG, or WEBP extension.')
                continue
            uploaded_images[filename.casefold()] = image

        if not catalog_file or not catalog_file.name.lower().endswith('.csv'):
            errors.append('Choose a CSV catalog file.')
        elif total_upload_size > 30 * 1024 * 1024 or catalog_file.size > 3 * 1024 * 1024:
            errors.append('Keep the CSV under 3 MB and the whole upload under 30 MB.')
        else:
            try:
                csv_content = catalog_file.read().decode('utf-8-sig')
                reader = csv.DictReader(io.StringIO(csv_content))
                required_columns = {'name', 'brand', 'category', 'description', 'price', 'available_sizes', 'image_filename'}
                headers = [field.strip().lower() for field in reader.fieldnames or []]
                if not headers or not required_columns.issubset(set(headers)):
                    errors.append('CSV needs these headers: name, brand, category, description, price, available_sizes, image_filename.')
                else:
                    reader.fieldnames = headers
                    for row_number, raw_row in enumerate(reader, start=2):
                        row = {str(key or '').strip().lower(): str(value or '').strip() for key, value in raw_row.items()}
                        try:
                            name = row.get('name', '')
                            description = row.get('description', '')
                            brand = Brand.objects.filter(name__iexact=row.get('brand', '')).first()
                            category = Category.objects.filter(name__iexact=row.get('category', '')).first()
                            price = Decimal(row.get('price', ''))
                            discount_text = row.get('discount_price', '')
                            discount_price = Decimal(discount_text) if discount_text else None
                            stock = int(row.get('stock', '0') or '0')
                            image_name = row.get('image_filename', '')
                            image = uploaded_images.get(image_name.casefold())
                            gender = row.get('gender', 'unisex').lower() or 'unisex'
                            variants = []
                            variant_text = row.get('variants', '')
                            if variant_text:
                                seen_variants = set()
                                for spec in variant_text.split(';'):
                                    pieces = [piece.strip() for piece in spec.split('|')]
                                    if len(pieces) not in (3, 4):
                                        raise ValueError('variants must use size|color|stock[|price], separated by semicolons')
                                    size, color = pieces[0], pieces[1]
                                    variant_stock = int(pieces[2])
                                    variant_price = Decimal(pieces[3]) if len(pieces) == 4 and pieces[3] else None
                                    if not size or not color or variant_stock < 0 or (variant_price is not None and variant_price <= 0):
                                        raise ValueError('each variant needs a size, color, non-negative stock, and positive optional price')
                                    if (size, color.casefold()) in seen_variants:
                                        raise ValueError('duplicate size and color variant')
                                    seen_variants.add((size, color.casefold()))
                                    variants.append((size, color, variant_stock, variant_price))
                            sizes = row.get('available_sizes', '') or ','.join(dict.fromkeys(item[0] for item in variants))
                            if not name or not description or not brand or not category or price <= 0 or stock < 0 or not image or not sizes:
                                raise ValueError('check name, existing brand/category, description, positive price, sizes, stock, and uploaded image filename')
                            from PIL import Image

                            image.seek(0)
                            with Image.open(image) as opened_image:
                                opened_image.verify()
                            image.seek(0)
                            if gender not in dict(Product.GENDER_CHOICES):
                                raise ValueError('gender must be men, women, kids, or unisex')
                            if discount_price is not None and (discount_price <= 0 or discount_price > price):
                                raise ValueError('discount_price must be positive and no higher than price')
                            with transaction.atomic():
                                product = Product.objects.create(
                                    shop=shop,
                                    name=name,
                                    name_hi=row.get('name_hi', ''),
                                    brand=brand,
                                    category=category,
                                    gender=gender,
                                    description=description,
                                    description_hi=row.get('description_hi', ''),
                                    price=price,
                                    discount_price=discount_price,
                                    stock=stock if not variants else 0,
                                    available_sizes=sizes,
                                    is_active=True,
                                )
                                image.seek(0)
                                product.image.save(os.path.basename(image.name), image, save=True)
                                for size, color, variant_stock, variant_price in variants:
                                    ProductVariant.objects.create(
                                        product=product,
                                        size=size,
                                        color=color,
                                        stock=variant_stock,
                                        price_override=variant_price,
                                    )
                            imported_count += 1
                        except (InvalidOperation, TypeError, ValueError) as exc:
                            errors.append(f'Row {row_number}: {exc}')
                        except (OSError, ValueError) as exc:
                            errors.append(f'Row {row_number}: could not import ({exc.__class__.__name__}).')
            except (UnicodeDecodeError, csv.Error, OSError) as exc:
                errors.append(f'Could not read the CSV file: {exc.__class__.__name__}. Save it as UTF-8 CSV and try again.')
            if imported_count:
                messages.success(request, f'Imported {imported_count} product row(s).')
            for error in errors[:10]:
                messages.error(request, error)
            return redirect('import_seller_catalog')
    return render(request, 'shops/catalog_import.html', {'shop': shop, 'errors': errors})


@login_required
def seller_delete_product(request, product_id):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    product = get_object_or_404(Product, pk=product_id, shop=shop)
    if request.method == 'POST':
        if product.marketplace_mappings.exists():
            messages.error(request, 'Remove its marketplace mappings before deleting this product.')
        else:
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
            variant = product.variants.filter(pk=request.POST.get('variant_id')).first()
            if variant and variant.marketplace_mappings.exists():
                messages.error(request, 'Remove this variant marketplace mapping before deleting the variant.')
            elif variant:
                variant.delete()
                messages.success(request, 'Variant removed.')
        return redirect('seller_manage_variants', product_id=product.pk)
    return render(request, 'shops/seller_variants.html', {
        'shop': shop,
        'product': product,
        'variants': product.variants.order_by('size', 'color'),
    })


@login_required
def marketplace_hub(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    channel_rows = []
    for channel, label in MarketplaceConnection.CHANNEL_CHOICES:
        connection = shop.marketplace_connections.filter(channel=channel).first()
        channel_rows.append({
            'channel': channel,
            'label': label,
            'connection': connection,
            'last_run': connection.sync_runs.first() if connection else None,
        })
    return render(request, 'shops/marketplaces.html', {'shop': shop, 'channel_rows': channel_rows})


@login_required
@require_POST
def save_flipkart_fulfillment_location(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    connection = get_object_or_404(MarketplaceConnection, shop=shop, channel='flipkart', status='approved')
    location_id = request.POST.get('fulfillment_location_id', '').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', location_id):
        messages.error(request, 'Enter the Flipkart location ID from the seller onboarding account.')
    else:
        connection.fulfillment_location_id = location_id
        connection.save(update_fields=['fulfillment_location_id', 'updated_at'])
        messages.success(request, 'Flipkart fulfillment location saved.')
    return redirect('marketplace_hub')


@login_required
@require_POST
def run_marketplace_sync(request, connection_id):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    connection = get_object_or_404(
        MarketplaceConnection, pk=connection_id, shop=shop, status='approved', authorization_status='connected',
    )
    from .marketplace_sync import sync_marketplace_connection

    run = sync_marketplace_connection(connection)
    if run.status == 'succeeded':
        messages.success(request, f'Sync complete: {run.orders_seen} orders, {run.order_items_seen} items, {run.inventory_updates} listing stock updates.')
        if run.error_summary:
            messages.warning(request, 'Some listing updates need attention. Review the product catalog mappings.')
    else:
        messages.error(request, run.error_summary or 'Marketplace sync failed.')
    return redirect('marketplace_hub')


@login_required
def marketplace_channel_orders(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if request.method == 'POST':
        channel_order = get_object_or_404(
            MarketplaceChannelOrder,
            pk=request.POST.get('order_id'),
            connection__shop=shop,
        )
        fee_text = request.POST.get('marketplace_fee', '').strip()
        settlement_text = request.POST.get('settlement_amount', '').strip()
        reference = request.POST.get('settlement_reference', '').strip()
        try:
            fee = Decimal(fee_text) if fee_text else None
            settlement = Decimal(settlement_text) if settlement_text else None
            if fee is not None and fee < 0:
                raise InvalidOperation
            if any(value is not None and abs(value) >= Decimal('10000000000') for value in (fee, settlement)):
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Enter valid fee and settlement amounts.')
        else:
            is_reconciled = fee is not None and settlement is not None and bool(reference)
            channel_order.marketplace_fee = fee
            channel_order.settlement_amount = settlement
            channel_order.settlement_reference = reference[:160]
            channel_order.reconciliation_status = 'reconciled' if is_reconciled else 'open'
            channel_order.reconciled_at = timezone.now() if is_reconciled else None
            channel_order.save(update_fields=[
                'marketplace_fee', 'settlement_amount', 'settlement_reference',
                'reconciliation_status', 'reconciled_at',
            ])
            messages.success(request, 'Marketplace fee and settlement reconciliation saved.')
        return redirect('marketplace_channel_orders')
    orders = MarketplaceChannelOrder.objects.filter(
        connection__shop=shop,
    ).select_related('connection').prefetch_related('items').order_by('-purchased_at', '-created_at')[:100]
    local_orders = SellerOrder.objects.filter(shop=shop).select_related('order').prefetch_related('items').order_by('-created_at')[:100]
    return render(request, 'shops/marketplace_orders.html', {
        'shop': shop,
        'orders': orders,
        'local_orders': local_orders,
    })


@login_required
@require_POST
def save_amazon_marketplace_ids(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    connection = get_object_or_404(MarketplaceConnection, shop=shop, channel='amazon', status='approved')
    submitted = request.POST.get('amazon_marketplace_ids', '').upper()
    marketplace_ids = list(dict.fromkeys(value.strip() for value in submitted.split(',') if value.strip()))
    if len(marketplace_ids) != 1 or any(not re.fullmatch(r'[A-Z0-9_-]{5,20}', value) for value in marketplace_ids):
        messages.error(request, 'Enter exactly one Amazon marketplace ID for shared Jaunpur stock synchronization.')
    else:
        connection.amazon_marketplace_ids = ','.join(marketplace_ids)
        connection.save(update_fields=['amazon_marketplace_ids', 'updated_at'])
        messages.success(request, 'Amazon marketplace IDs saved for this seller account.')
    return redirect('marketplace_hub')


@login_required
@require_POST
def start_amazon_authorization(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    connection = get_object_or_404(MarketplaceConnection, shop=shop, channel='amazon', status='approved')
    if not all((settings.AMAZON_APPLICATION_ID, settings.AMAZON_LWA_CLIENT_ID, settings.AMAZON_LWA_CLIENT_SECRET, settings.AMAZON_REDIRECT_URI)):
        messages.error(request, 'Amazon app registration, LWA credentials, and callback URL are not configured yet.')
        return redirect('marketplace_hub')
    if not marketplace_encryption_is_configured():
        messages.error(request, 'Set a valid marketplace token encryption key before connecting a seller account.')
        return redirect('marketplace_hub')
    if not connection.amazon_marketplace_ids:
        messages.error(request, 'Save at least one Amazon marketplace ID before starting seller authorization.')
        return redirect('marketplace_hub')
    state = signing.dumps({
        'connection_id': connection.pk,
        'owner_id': request.user.pk,
        'nonce': secrets.token_urlsafe(24),
    }, salt='marketplace-amazon-oauth', compress=True)
    request.session['amazon_oauth_state'] = state
    authorization_params = {'application_id': settings.AMAZON_APPLICATION_ID, 'state': state}
    if settings.AMAZON_OAUTH_VERSION == 'beta':
        authorization_params['version'] = 'beta'
    query = urlencode(authorization_params)
    return redirect(f'{settings.AMAZON_AUTHORIZATION_URL}?{query}')


@login_required
@require_GET
def amazon_authorization_callback(request):
    state = request.GET.get('state', '')
    expected_state = request.session.pop('amazon_oauth_state', '')
    if not state or state != expected_state:
        messages.error(request, 'Amazon authorization could not be verified. Start the connection again.')
        return redirect('marketplace_hub')
    try:
        state_data = signing.loads(state, salt='marketplace-amazon-oauth', max_age=900)
    except signing.BadSignature:
        messages.error(request, 'Amazon authorization expired. Start the connection again.')
        return redirect('marketplace_hub')
    if state_data.get('owner_id') != request.user.pk:
        messages.error(request, 'This Amazon authorization belongs to a different seller account.')
        return redirect('marketplace_hub')
    connection = MarketplaceConnection.objects.filter(
        pk=state_data.get('connection_id'), shop__owner=request.user, channel='amazon', status='approved',
    ).first()
    if not connection:
        messages.error(request, 'The approved Amazon seller setup could not be found.')
        return redirect('marketplace_hub')
    if request.GET.get('error'):
        messages.error(request, 'Amazon seller authorization was declined or cancelled.')
        return redirect('marketplace_hub')
    code = request.GET.get('spapi_oauth_code', request.GET.get('code', '')).strip()
    seller_id = request.GET.get('selling_partner_id', '').strip()
    if not code or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', seller_id):
        messages.error(request, 'Amazon did not return a valid authorization code and selling partner ID.')
        return redirect('marketplace_hub')
    callback_ids = request.GET.getlist('marketplaceIds') or request.GET.getlist('marketplace_ids')
    if callback_ids:
        callback_ids = list(dict.fromkeys(
            value.strip().upper()
            for raw_value in callback_ids
            for value in raw_value.split(',')
            if value.strip()
        ))
        if len(callback_ids) != 1 or any(not re.fullmatch(r'[A-Z0-9_-]{5,20}', value) for value in callback_ids):
            messages.error(request, 'Amazon returned marketplace IDs in an unsupported format.')
            return redirect('marketplace_hub')
        connection.amazon_marketplace_ids = ','.join(callback_ids)
    try:
        token_data = exchange_amazon_code(code)
        expires_in = max(0, int(token_data.get('expires_in', 0)))
        connection.encrypted_access_token = encrypt_marketplace_token(token_data['access_token'])
        connection.encrypted_refresh_token = encrypt_marketplace_token(token_data['refresh_token'])
    except (MarketplaceAuthorizationError, TypeError, ValueError):
        messages.error(request, 'Amazon connection failed. Check the app setup and try again.')
        return redirect('marketplace_hub')
    connection.seller_account_id = seller_id
    connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in) if expires_in else None
    connection.refresh_token_expires_at = timezone.now() + timedelta(days=365)
    connection.authorization_status = 'connected'
    connection.authorized_at = timezone.now()
    connection.save(update_fields=[
        'seller_account_id', 'amazon_marketplace_ids', 'encrypted_access_token', 'encrypted_refresh_token',
        'token_expires_at', 'refresh_token_expires_at', 'authorization_status', 'authorized_at', 'updated_at',
    ])
    messages.success(request, 'The Amazon seller account authorized this shop. Product, stock, and order synchronization is the next setup step.')
    return redirect('marketplace_hub')


@login_required
@require_POST
def disconnect_amazon(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    connection = get_object_or_404(MarketplaceConnection, shop=shop, channel='amazon', status='approved')
    connection.encrypted_access_token = ''
    connection.encrypted_refresh_token = ''
    connection.token_expires_at = None
    connection.refresh_token_expires_at = None
    connection.authorized_at = None
    connection.authorization_status = 'not_connected'
    connection.save(update_fields=[
        'encrypted_access_token', 'encrypted_refresh_token', 'token_expires_at', 'refresh_token_expires_at',
        'authorized_at', 'authorization_status', 'updated_at',
    ])
    messages.success(request, 'The Amazon authorization was removed from this Jaunpur shop.')
    return redirect('marketplace_hub')


@login_required
@require_POST
def start_flipkart_authorization(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    connection = get_object_or_404(MarketplaceConnection, shop=shop, channel='flipkart', status='approved')
    if not all((settings.FLIPKART_CLIENT_ID, settings.FLIPKART_CLIENT_SECRET, settings.FLIPKART_REDIRECT_URI)):
        messages.error(request, 'Flipkart developer app credentials and callback URL are not configured yet.')
        return redirect('marketplace_hub')
    if not marketplace_encryption_is_configured():
        messages.error(request, 'Set a valid marketplace token encryption key before connecting a seller account.')
        return redirect('marketplace_hub')

    state = signing.dumps({
        'connection_id': connection.pk,
        'owner_id': request.user.pk,
        'nonce': secrets.token_urlsafe(24),
    }, salt='marketplace-flipkart-oauth', compress=True)
    request.session['flipkart_oauth_state'] = state
    query = urlencode({
        'client_id': settings.FLIPKART_CLIENT_ID,
        'redirect_uri': settings.FLIPKART_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'Seller_Api',
        'state': state,
    })
    return redirect(f'{settings.FLIPKART_AUTHORIZATION_URL}?{query}')


@login_required
@require_GET
def flipkart_authorization_callback(request):
    state = request.GET.get('state', '')
    expected_state = request.session.pop('flipkart_oauth_state', '')
    if not state or state != expected_state:
        messages.error(request, 'Flipkart authorization could not be verified. Start the connection again.')
        return redirect('marketplace_hub')
    try:
        state_data = signing.loads(state, salt='marketplace-flipkart-oauth', max_age=900)
    except signing.BadSignature:
        messages.error(request, 'Flipkart authorization expired. Start the connection again.')
        return redirect('marketplace_hub')
    if state_data.get('owner_id') != request.user.pk:
        messages.error(request, 'This Flipkart authorization belongs to a different seller account.')
        return redirect('marketplace_hub')
    connection = MarketplaceConnection.objects.filter(
        pk=state_data.get('connection_id'), shop__owner=request.user, channel='flipkart', status='approved',
    ).first()
    if not connection:
        messages.error(request, 'The approved Flipkart seller setup could not be found.')
        return redirect('marketplace_hub')
    if request.GET.get('error'):
        messages.error(request, 'Flipkart seller authorization was declined or cancelled.')
        return redirect('marketplace_hub')
    code = request.GET.get('code', '').strip()
    if not code:
        messages.error(request, 'Flipkart did not return an authorization code.')
        return redirect('marketplace_hub')
    try:
        token_data = exchange_flipkart_code(code, state)
        expires_in = max(0, int(token_data.get('expires_in', 0)))
        connection.encrypted_access_token = encrypt_marketplace_token(token_data['access_token'])
        connection.encrypted_refresh_token = encrypt_marketplace_token(token_data.get('refresh_token', ''))
    except (MarketplaceAuthorizationError, TypeError, ValueError):
        messages.error(request, 'Flipkart connection failed. Check the app setup and try again.')
        return redirect('marketplace_hub')
    connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in) if expires_in else None
    refresh_expires_in = token_data.get('refresh_token_expires_in')
    connection.refresh_token_expires_at = timezone.now() + timedelta(seconds=max(0, int(refresh_expires_in))) if refresh_expires_in else None
    connection.authorization_status = 'connected'
    connection.authorized_at = timezone.now()
    connection.save(update_fields=[
        'encrypted_access_token', 'encrypted_refresh_token', 'token_expires_at', 'refresh_token_expires_at',
        'authorization_status', 'authorized_at', 'updated_at',
    ])
    messages.success(request, 'The Flipkart seller account authorized this shop. Product, stock, and order synchronization is the next setup step.')
    return redirect('marketplace_hub')


@login_required
@require_POST
def disconnect_flipkart(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    connection = get_object_or_404(MarketplaceConnection, shop=shop, channel='flipkart', status='approved')
    connection.encrypted_access_token = ''
    connection.encrypted_refresh_token = ''
    connection.token_expires_at = None
    connection.refresh_token_expires_at = None
    connection.authorized_at = None
    connection.authorization_status = 'not_connected'
    connection.save(update_fields=[
        'encrypted_access_token', 'encrypted_refresh_token', 'token_expires_at', 'refresh_token_expires_at',
        'authorized_at', 'authorization_status', 'updated_at',
    ])
    messages.success(request, 'The Flipkart authorization was removed from this Jaunpur shop.')
    return redirect('marketplace_hub')


@login_required
def manage_marketplace_catalog(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    connections = shop.marketplace_connections.filter(status='approved')
    error = ''
    if request.method == 'POST':
        if request.POST.get('action') == 'remove_mapping':
            mapping = get_object_or_404(MarketplaceProductMapping, pk=request.POST.get('mapping_id'), connection__shop=shop)
            if mapping.allocated_quantity or mapping.status != 'draft':
                messages.error(request, 'Only draft marketplace mappings with zero reserved stock can be removed. Deactivate submitted listings in the marketplace first.')
            else:
                mapping.delete()
                messages.success(request, 'Marketplace product mapping removed.')
            return redirect('manage_marketplace_catalog')
        if request.POST.get('action') == 'update_allocation':
            mapping = get_object_or_404(MarketplaceProductMapping, pk=request.POST.get('mapping_id'), connection__shop=shop)
            try:
                allocation = int(request.POST.get('allocated_quantity', ''))
            except (TypeError, ValueError):
                allocation = -1
            if allocation < 0:
                messages.error(request, 'Enter a non-negative marketplace stock allocation.')
            elif not update_mapping_allocation(mapping, allocation):
                messages.error(request, 'Marketplace allocations cannot exceed the current shared stock for this product or variant.')
            else:
                messages.success(request, f'{mapping.external_sku} now reserves {allocation} unit(s) for {mapping.connection.get_channel_display()}.')
            return redirect('manage_marketplace_catalog')
        try:
            connection_id = int(request.POST.get('connection_id', ''))
            product_id = int(request.POST.get('product_id', ''))
            variant_id = int(request.POST.get('variant_id')) if request.POST.get('variant_id', '').strip() else None
            allocated_quantity = int(request.POST.get('allocated_quantity', '0'))
        except (TypeError, ValueError):
            connection_id, product_id, variant_id = 0, 0, None
            allocated_quantity = -1
            error = 'Choose a valid marketplace product and variant.'
        connection = connections.filter(pk=connection_id).first()
        product = shop.products.filter(is_active=True, pk=product_id).first()
        variant = None
        if variant_id and product:
            variant = product.variants.filter(is_active=True, pk=variant_id).first()
        external_sku = request.POST.get('external_sku', '').strip()
        category_path = request.POST.get('category_path', '').strip()
        external_listing_id = request.POST.get('external_listing_id', '').strip()
        has_variants = product.variants.filter(is_active=True).exists() if product else False
        if error:
            pass
        elif not connection or not product or (variant_id and not variant) or (has_variants and not variant) or not external_sku or allocated_quantity < 0:
            error = 'Choose an approved marketplace, map each size/color variant, enter a marketplace SKU, and use a non-negative stock allocation.'
        else:
            mapping = MarketplaceProductMapping.objects.filter(
                connection=connection,
                product=product,
                variant=variant,
            ).first()
            duplicate_skus = MarketplaceProductMapping.objects.filter(connection=connection, external_sku=external_sku)
            if mapping:
                duplicate_skus = duplicate_skus.exclude(pk=mapping.pk)
            duplicate_sku = duplicate_skus.exists()
            if duplicate_sku:
                error = 'That marketplace SKU is already mapped to another item in this seller account.'
            else:
                if mapping is None:
                    mapping = MarketplaceProductMapping(connection=connection, product=product, variant=variant)
                mapping.external_sku = external_sku
                mapping.category_path = category_path
                mapping.external_listing_id = external_listing_id
                mapping.status = 'draft'
                mapping.error_text = ''
                mapping.save()
                if not update_mapping_allocation(mapping, allocated_quantity):
                    error = 'The allocations across connected channels cannot exceed current product or variant stock.'
                else:
                    messages.success(request, f'Marketplace SKU mapping saved for {product.name}.')
                    return redirect('manage_marketplace_catalog')
    return render(request, 'shops/marketplace_catalog.html', {
        'shop': shop,
        'connections': connections,
        'products': shop.products.filter(is_active=True).prefetch_related('variants').order_by('name'),
        'mappings': MarketplaceProductMapping.objects.filter(connection__shop=shop).select_related('connection', 'product', 'variant'),
        'error': error,
    })


@login_required
def request_marketplace_setup(request, channel):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if request.method == 'POST' and channel in dict(MarketplaceConnection.CHANNEL_CHOICES):
        connection, _ = MarketplaceConnection.objects.get_or_create(shop=shop, channel=channel)
        if connection.status != 'approved':
            connection.seller_account_id = request.POST.get('seller_account_id', '').strip()
            connection.status = 'pending'
            connection.requested_at = timezone.now()
            connection.save(update_fields=['seller_account_id', 'status', 'requested_at', 'updated_at'])
            messages.success(request, 'Marketplace setup request sent to the Jaunpur Footwear admin.')
        else:
            messages.info(request, 'Your seller setup has already been reviewed.')
    return redirect('marketplace_hub')


@login_required
def export_marketplace_feed(request, channel):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if channel not in dict(MarketplaceConnection.CHANNEL_CHOICES):
        return redirect('marketplace_hub')
    connection = get_object_or_404(MarketplaceConnection, shop=shop, channel=channel, status='approved')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="jaunpur-{channel}-catalog.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['seller_sku', 'marketplace_sku', 'marketplace_category', 'shop_name', 'product_name', 'brand', 'category', 'description', 'price_inr', 'quantity', 'size', 'color'])
    products = shop.products.filter(is_active=True).select_related('brand', 'category').prefetch_related('variants')
    for product in products:
        variants = list(product.variants.filter(is_active=True))
        if variants:
            for variant in variants:
                mapping = MarketplaceProductMapping.objects.filter(connection=connection, product=product, variant=variant).first()
                writer.writerow([
                    variant.seller_sku, mapping.external_sku if mapping else '', mapping.category_path if mapping else '', shop.name, product.name,
                    product.brand.name, product.category.name, product.description,
                    variant.final_price(), mapping.allocated_quantity if mapping else 0, variant.size, variant.color,
                ])
        else:
            mapping = MarketplaceProductMapping.objects.filter(connection=connection, product=product, variant__isnull=True).first()
            writer.writerow([
                product.seller_sku, mapping.external_sku if mapping else '', mapping.category_path if mapping else '', shop.name, product.name,
                product.brand.name, product.category.name, product.description,
                product.final_price(), mapping.allocated_quantity if mapping else 0, '', '',
            ])
    return response


@login_required
def ondc_setup(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    enrollment, _ = ONDCEnrollment.objects.get_or_create(shop=shop)
    if request.method == 'POST':
        participant_name = request.POST.get('participant_name', '').strip()
        participant_contact = request.POST.get('participant_contact', '').strip()
        if not participant_name or not participant_contact:
            messages.error(request, 'Enter the Seller Network Participant name and a contact detail.')
        else:
            participant_values = {
                'participant_name': participant_name[:160],
                'participant_contact': participant_contact[:160],
                'seller_network_id': request.POST.get('seller_network_id', '').strip()[:120],
                'participant_seller_id': request.POST.get('participant_seller_id', '').strip()[:120],
                'network_subscriber_id': request.POST.get('network_subscriber_id', '').strip()[:120],
                'application_reference': request.POST.get('application_reference', '').strip()[:120],
            }
            identity_fields = (
                'participant_name', 'participant_contact', 'seller_network_id',
                'participant_seller_id', 'network_subscriber_id',
            )
            participant_changed = any(
                getattr(enrollment, field) != participant_values[field]
                for field in identity_fields
            )
            for field, value in participant_values.items():
                setattr(enrollment, field, value)
            if participant_changed or enrollment.status in ('draft', 'needs_changes'):
                enrollment.status = 'submitted'
                enrollment.submitted_at = timezone.now()
                enrollment.participant_supports_retail = False
                enrollment.catalog_exported_at = None
                enrollment.production_activated_at = None
            enrollment.save(update_fields=[
                'participant_name', 'participant_contact', 'seller_network_id', 'participant_seller_id',
                'network_subscriber_id', 'application_reference', 'participant_supports_retail', 'status',
                'submitted_at', 'catalog_exported_at', 'production_activated_at', 'updated_at',
            ])
            messages.success(request, 'Seller Network Participant details were saved for Jaunpur admin review.')
            return redirect('ondc_setup')
    readiness = _ondc_catalog_readiness(shop)
    participant_confirmed = enrollment.status in (
        'partner_confirmed', 'catalog_exported', 'production_approval_pending', 'live',
    ) and enrollment.participant_supports_retail
    return render(request, 'shops/ondc_setup.html', {
        'shop': shop,
        'enrollment': enrollment,
        'readiness': readiness,
        'participant_confirmed': participant_confirmed,
        'can_export_catalog': participant_confirmed and readiness['ready'],
    })


def _ondc_catalog_readiness(shop):
    products = list(shop.products.filter(is_active=True).select_related('brand', 'category').prefetch_related('variants'))
    active_product_count = len(products)
    missing_skus = []
    missing_images = []
    inactive_variant_products = []
    zero_stock_count = 0
    missing_hindi_count = 0
    for product in products:
        all_variants = list(product.variants.all())
        variants = [variant for variant in all_variants if variant.is_active]
        if all_variants and not variants:
            inactive_variant_products.append(product.name)
        if variants and not any(variant.stock > 0 for variant in variants):
            zero_stock_count += 1
        elif not all_variants and product.stock <= 0:
            zero_stock_count += 1
        if variants and any(not variant.seller_sku for variant in variants):
            missing_skus.append(product.name)
        elif not variants and not product.seller_sku:
            missing_skus.append(product.name)
        if not product.image:
            missing_images.append(product.name)
        if not product.description_hi and not product.name_hi:
            missing_hindi_count += 1

    checklist = [
        {
            'label': 'Shop profile is approved and verified in Jaunpur',
            'ready': shop.status == 'approved' and shop.verification_status == 'verified',
            'detail': 'A verified Jaunpur seller profile is required before production onboarding.',
        },
        {
            'label': 'Shop contact, address, and PIN code are complete',
            'ready': bool(shop.phone and shop.address and re.fullmatch(r'[1-9][0-9]{5}', shop.pincode or '')),
            'detail': 'The participant needs a shop contact and Jaunpur location.',
        },
        {
            'label': 'At least one active product is listed',
            'ready': active_product_count > 0,
            'detail': f'{active_product_count} active product(s) found.',
        },
        {
            'label': 'Every active listing has a seller SKU and product image',
            'ready': not missing_skus and not missing_images and not inactive_variant_products,
            'detail': '; '.join(filter(None, [
                f'Seller SKU missing: {", ".join(missing_skus[:5])}' if missing_skus else '',
                f'Image missing: {", ".join(missing_images[:5])}' if missing_images else '',
                f'No active size/color variants: {", ".join(inactive_variant_products[:5])}' if inactive_variant_products else '',
            ])) or 'Catalog identifiers and images are present.',
        },
        {
            'label': 'Seller Network Participant details are recorded',
            'ready': bool(shop.ondc_enrollment.participant_name and shop.ondc_enrollment.participant_contact),
            'detail': 'Add the participant name and an email or phone contact.',
        },
        {
            'label': 'Participant confirmed ONDC retail support',
            'ready': shop.ondc_enrollment.participant_supports_retail,
            'detail': 'The Jaunpur admin must confirm the selected participant supports the retail domain.',
        },
    ]
    blockers = [item['detail'] for item in checklist if not item['ready']]
    warnings = []
    if zero_stock_count:
        warnings.append(f'{zero_stock_count} product(s) currently have no sellable stock; restock them before launch.')
    if missing_hindi_count:
        warnings.append(f'{missing_hindi_count} product(s) have no Hindi name or description.')
    if not shop.coverage_areas.filter(is_active=True).exists():
        warnings.append('No Jaunpur delivery PIN-code coverage areas are configured yet.')
    return {
        'checklist': checklist,
        'blockers': blockers,
        'warnings': warnings,
        'ready': not blockers,
        'product_count': active_product_count,
    }


@login_required
@require_POST
def export_ondc_catalog(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    enrollment = get_object_or_404(ONDCEnrollment, shop=shop)
    participant_confirmed = enrollment.status in (
        'partner_confirmed', 'catalog_exported', 'production_approval_pending', 'live',
    ) and enrollment.participant_supports_retail
    readiness = _ondc_catalog_readiness(shop)
    if not participant_confirmed or not readiness['ready']:
        messages.error(request, 'Complete the ONDC readiness checklist and get participant eligibility confirmed before exporting.')
        return redirect('ondc_setup')

    products = shop.products.filter(is_active=True).select_related('brand', 'category').prefetch_related('variants').order_by('name')
    catalog_items = []
    for product in products:
        image_url = request.build_absolute_uri(product.image.url) if product.image else ''
        variants = [variant for variant in product.variants.all() if variant.is_active]
        base = {
            'product_name': product.name,
            'product_name_hi': product.name_hi,
            'description': product.description,
            'description_hi': product.description_hi,
            'brand': product.brand.name,
            'category': product.category.name,
            'image_url': image_url,
            'currency': 'INR',
        }
        if variants:
            for variant in variants:
                catalog_items.append({
                    **base,
                    'seller_sku': variant.seller_sku,
                    'price': str(variant.final_price()),
                    'available_stock_snapshot': local_available_stock(variant),
                    'size': variant.size,
                    'color': variant.color,
                })
        else:
            catalog_items.append({
                **base,
                'seller_sku': product.seller_sku,
                'price': str(product.final_price()),
                'available_stock_snapshot': local_available_stock(product),
                'size': '',
                'color': '',
            })

    payload = {
        'schema_version': 'jaunpur-footwear.ondc-seller-handoff.v1',
        'generated_at': timezone.now().isoformat(),
        'purpose': 'Seller catalog snapshot for manual handoff to the confirmed Seller Network Participant.',
        'seller': {
            'shop_name': shop.name,
            'shop_id': shop.pk,
            'jaunpur_verified': shop.verification_status == 'verified',
            'phone': shop.phone,
            'email': shop.email,
            'address': shop.address,
            'city': shop.city,
            'district': shop.district,
            'pincode': shop.pincode,
            'seller_network_id': enrollment.seller_network_id,
            'participant_seller_id': enrollment.participant_seller_id,
            'network_subscriber_id': enrollment.network_subscriber_id,
            'application_reference': enrollment.application_reference,
        },
        'jaunpur_delivery_areas': [
            {'pincode': area.pincode, 'area_name': area.area_name, 'delivery_fee_inr': str(area.delivery_fee)}
            for area in shop.coverage_areas.filter(is_active=True).order_by('pincode')
        ],
        'stock_note': 'Available stock values are a point-in-time snapshot after existing marketplace reservations; arrange participant order and inventory synchronization before production traffic.',
        'products': catalog_items,
    }
    if enrollment.status == 'partner_confirmed':
        enrollment.status = 'catalog_exported'
        enrollment.catalog_exported_at = timezone.now()
        enrollment.save(update_fields=['status', 'catalog_exported_at', 'updated_at'])
    elif enrollment.catalog_exported_at is None:
        enrollment.catalog_exported_at = timezone.now()
        enrollment.save(update_fields=['catalog_exported_at', 'updated_at'])
    response = HttpResponse(json.dumps(payload, ensure_ascii=False, indent=2), content_type='application/json; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="jaunpur-ondc-{shop.slug}-catalog.json"'
    return response


def set_site_language(request, language):
    if language in ('en', 'hi'):
        request.session['site_language'] = language
    next_url = request.GET.get('next', '/')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = reverse('home')
    return redirect(next_url)


@login_required
def seller_shop_profile(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if request.method == 'POST':
        shop.description = request.POST.get('description', '').strip()
        shop.description_hi = request.POST.get('description_hi', '').strip()
        shop.opening_hours = request.POST.get('opening_hours', '').strip()
        if request.FILES.get('logo'):
            shop.logo = request.FILES['logo']
        if request.FILES.get('banner'):
            shop.banner = request.FILES['banner']
        shop.save(update_fields=['description', 'description_hi', 'opening_hours', 'logo', 'banner', 'updated_at'])
        messages.success(request, 'Your bilingual shop profile was saved.')
        return redirect('seller_shop_profile')
    return render(request, 'shops/seller_profile.html', {'shop': shop})


def _parse_local_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


@login_required
def manage_promotions(request):
    shop = get_object_or_404(Shop, owner=request.user, status='approved')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        title_hi = request.POST.get('title_hi', '').strip()
        description = request.POST.get('description', '').strip()
        description_hi = request.POST.get('description_hi', '').strip()
        discount_type = request.POST.get('discount_type', '')
        target_pincodes = sorted(set(request.POST.getlist('target_pincodes')))
        covered_pincodes = set(shop.coverage_areas.filter(is_active=True).values_list('pincode', flat=True))
        try:
            product_ids = [int(value) for value in request.POST.getlist('products')]
        except (TypeError, ValueError):
            product_ids = []
        products = shop.products.filter(is_active=True, pk__in=product_ids)
        try:
            discount_value = Decimal(request.POST.get('discount_value', ''))
            starts_at = _parse_local_datetime(request.POST.get('starts_at', ''))
            expires_at = _parse_local_datetime(request.POST.get('expires_at', ''))
        except (InvalidOperation, TypeError, ValueError):
            discount_value, starts_at, expires_at = Decimal('0.00'), None, None
            messages.error(request, 'Enter a valid discount and schedule.')
        else:
            valid_discount = discount_value > 0 and (discount_type != 'percent' or discount_value <= 100)
            valid_schedule = starts_at is None or expires_at is None or expires_at > starts_at
            if not title or discount_type not in ('percent', 'fixed') or not valid_discount or not valid_schedule or not product_ids or products.count() != len(set(product_ids)) or not set(target_pincodes).issubset(covered_pincodes):
                messages.error(request, 'Choose your products, a title, a positive discount, and a valid date range.')
            else:
                promotion = ShopPromotion.objects.create(
                    shop=shop,
                    title=title,
                    title_hi=title_hi,
                    description=description,
                    description_hi=description_hi,
                    discount_type=discount_type,
                    discount_value=discount_value,
                    target_pincodes=','.join(target_pincodes),
                    starts_at=starts_at,
                    expires_at=expires_at,
                )
                promotion.products.set(products)
                messages.success(request, 'Jaunpur shop promotion published.')
                return redirect('manage_promotions')
    return render(request, 'shops/promotions.html', {
        'shop': shop,
        'products': shop.products.filter(is_active=True).order_by('name'),
        'promotions': shop.promotions.prefetch_related('products').all(),
        'discount_types': ShopPromotion.DISCOUNT_TYPES,
        'coverage_areas': shop.coverage_areas.filter(is_active=True).order_by('pincode'),
    })


@login_required
def deactivate_promotion(request, promotion_id):
    promotion = get_object_or_404(ShopPromotion, pk=promotion_id, shop__owner=request.user, shop__status='approved')
    if request.method == 'POST':
        promotion.is_active = False
        promotion.save(update_fields=['is_active'])
        messages.success(request, 'Promotion closed. Its prices no longer apply to new carts.')
    return redirect('manage_promotions')
