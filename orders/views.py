from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from datetime import date, timedelta
from django.conf import settings
from decimal import Decimal
import re
import uuid
from products.models import Product, ProductVariant
from .models import CartItem, Coupon, DeliveryAssignment, DeliveryRate, DeliveryRider, Order, OrderItem, OrderTrackingEvent, PaymentAttempt, ReturnRequest, SellerOrder
from .notifications import send_order_confirmation, send_order_status_update
from .payments import (
    PaymentGatewayError,
    create_razorpay_order,
    fetch_razorpay_payment,
    release_order_inventory,
    verify_razorpay_signature,
)
from shops.models import ShopCoverage, ShopFulfillmentSlot
from accounts.models import ReferralReward
from accounts.services import award_loyalty_for_order


def delivery_fee_for(pincode, subtotal):
    rates = DeliveryRate.objects.filter(is_active=True)
    matching_rates = [rate for rate in rates if pincode.startswith(rate.pincode_prefix)]
    if matching_rates:
        rate = max(matching_rates, key=lambda item: len(item.pincode_prefix))
        if rate.free_delivery_minimum is not None and subtotal >= rate.free_delivery_minimum:
            return Decimal('0.00')
        return rate.fee
    return Decimal(str(getattr(settings, 'DEFAULT_DELIVERY_FEE', '50.00')))


def checkout_seller_groups(items, pincode=''):
    groups = {}
    for item in items:
        shop = item.product.shop if item.product.shop_id else None
        key = shop.pk if shop else None
        if key not in groups:
            groups[key] = {'key': str(key) if key else 'platform', 'shop': shop, 'subtotal': Decimal('0.00')}
        unit_price = item.variant.final_price(pincode=pincode) if item.variant_id else item.product.final_price(pincode=pincode)
        groups[key]['subtotal'] += unit_price * item.quantity
    result = []
    for group in groups.values():
        shop = group['shop']
        coverage = ShopCoverage.objects.filter(shop=shop, pincode=pincode, is_active=True).first() if shop and pincode else None
        slots = list(shop.fulfillment_slots.filter(is_active=True)) if shop else []
        group['coverage'] = coverage
        group['slots'] = slots
        has_delivery_slot = any(slot.mode == 'delivery' for slot in slots)
        group['delivery_available'] = (coverage is not None and has_delivery_slot) if pincode else (
            bool(shop.coverage_areas.filter(is_active=True).exists()) and has_delivery_slot if shop else True
        )
        group['pickup_available'] = any(slot.mode == 'pickup' for slot in slots)
        group['default_method'] = 'delivery' if group['delivery_available'] else 'pickup' if group['pickup_available'] else 'delivery'
        if pincode:
            if shop and coverage:
                if coverage.free_delivery_minimum is not None and group['subtotal'] >= coverage.free_delivery_minimum:
                    group['delivery_fee_preview'] = Decimal('0.00')
                else:
                    group['delivery_fee_preview'] = coverage.delivery_fee
            elif not shop:
                group['delivery_fee_preview'] = delivery_fee_for(pincode, group['subtotal'])
            else:
                group['delivery_fee_preview'] = Decimal('0.00')
        else:
            group['delivery_fee_preview'] = Decimal('0.00')
        group['shipping_preview'] = group['delivery_fee_preview'] if group['default_method'] == 'delivery' else Decimal('0.00')
        result.append(group)
    return result


def resolve_checkout_fulfillment(items, pincode, post_data):
    selections = {}
    groups = {}
    for item in items:
        shop = item.product.shop if item.product.shop_id else None
        key = shop.pk if shop else None
        if key not in groups:
            groups[key] = {'shop': shop, 'subtotal': Decimal('0.00')}
        unit_price = item.variant.final_price(pincode=pincode) if item.variant_id else item.product.final_price(pincode=pincode)
        groups[key]['subtotal'] += unit_price * item.quantity

    for key, group in groups.items():
        shop = group['shop']
        form_key = str(key) if key else 'platform'
        method = post_data.get(f'fulfillment_{form_key}', 'delivery')
        subtotal = group['subtotal']
        if not shop:
            if method != 'delivery':
                return None, None, 'Choose delivery for the Jaunpur Footwear catalog items.'
            selections[key] = {
                'method': 'delivery',
                'date': None,
                'slot': None,
                'shipping': delivery_fee_for(pincode, subtotal),
            }
            continue

        if method not in ('delivery', 'pickup'):
            return None, None, f'Choose delivery or pickup for {shop.name}.'
        try:
            selected_date = date.fromisoformat(post_data.get(f'fulfillment_date_{form_key}', ''))
        except (TypeError, ValueError):
            return None, None, f'Choose a date for {shop.name}.'
        if selected_date < timezone.localdate():
            return None, None, 'Choose today or a future fulfillment date.'
        try:
            slot_id = int(post_data.get(f'fulfillment_slot_{form_key}', ''))
        except (TypeError, ValueError):
            return None, None, f'Choose a time slot for {shop.name}.'
        slot = ShopFulfillmentSlot.objects.select_for_update().filter(
            pk=slot_id,
            shop=shop,
            mode=method,
            weekday=selected_date.weekday(),
            is_active=True,
        ).first()
        if not slot:
            return None, None, f'That time slot is not available for {shop.name} on the selected date.'
        reserved_count = slot.seller_orders.filter(fulfillment_date=selected_date).exclude(order__status='cancelled').count()
        if reserved_count >= slot.max_orders:
            return None, None, f'That {shop.name} time slot is full. Choose another slot.'
        shipping = Decimal('0.00')
        if method == 'delivery':
            coverage = ShopCoverage.objects.filter(shop=shop, pincode=pincode, is_active=True).first()
            if not coverage:
                return None, None, f'{shop.name} does not deliver to PIN code {pincode}; choose pickup instead.'
            shipping = coverage.delivery_fee
            if coverage.free_delivery_minimum is not None and subtotal >= coverage.free_delivery_minimum:
                shipping = Decimal('0.00')
        selections[key] = {
            'method': method,
            'date': selected_date,
            'slot': slot,
            'shipping': shipping,
        }
    return selections, sum((item['shipping'] for item in selections.values()), Decimal('0.00')), None


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 0

        variant = None
        variant_id = request.POST.get('variant_id')
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product, is_active=True)
            size = variant.size
            color = variant.color
            available_stock = variant.stock
        else:
            size = request.POST.get('size', '').strip()
            color = request.POST.get('color', '').strip()
            available_stock = product.stock
            valid_sizes = [choice.strip() for choice in product.available_sizes.split(',') if choice.strip()]
            if size not in valid_sizes:
                messages.error(request, 'Choose one of the available shoe sizes.')
                return redirect('product_detail', pk=product.id)

        if quantity < 1 or not size:
            messages.error(request, 'Choose a shoe size and enter a valid quantity.')
            return redirect('product_detail', pk=product.id)

        if product.variants.filter(is_active=True).exists() and not variant:
            messages.error(request, 'Choose a size and color variant before adding this product.')
            return redirect('product_detail', pk=product.id)

        item = CartItem.objects.filter(
            user=request.user,
            product=product,
            size=size,
            color=color,
            variant=variant,
        ).first()
        requested_quantity = quantity + (item.quantity if item else 0)
        if requested_quantity > available_stock:
            messages.error(request, f'Only {available_stock} of this size and color are currently available.')
            return redirect('product_detail', pk=product.id)

        if item:
            item.quantity = requested_quantity
        else:
            item = CartItem(
                user=request.user,
                product=product,
                size=size,
                color=color,
                variant=variant,
                quantity=quantity,
            )

        item.save()

    return redirect('cart')


@login_required
def cart_view(request):
    items = CartItem.objects.filter(user=request.user)
    pincode = request.session.get('delivery_pincode', '')
    total = sum(item.total_price(pincode=pincode) for item in items)
    for item in items:
        item.current_unit_price = item.variant.final_price(pincode=pincode) if item.variant_id else item.product.final_price(pincode=pincode)
        item.current_total = item.current_unit_price * item.quantity

    return render(request, 'orders/cart.html', {
        'items': items,
        'total': total,
    })


@login_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    return redirect('cart')


@login_required
def checkout(request):
    items = CartItem.objects.filter(user=request.user).select_related('product__shop', 'variant')

    if not items.exists():
        return redirect('cart')

    pincode = request.session.get('delivery_pincode', '')
    total = sum(item.total_price(pincode=pincode) for item in items)
    coupon_code = request.session.get('coupon_code', '')
    coupon = Coupon.objects.filter(code__iexact=coupon_code).first() if coupon_code else None
    if coupon and coupon.is_valid_for(total, user=request.user):
        discount = coupon.discount_for(total)
    else:
        discount = 0
        if coupon_code:
            request.session.pop('coupon_code', None)
            coupon_code = ''
            messages.warning(request, 'The applied coupon is no longer valid.')

    checkout_sellers = checkout_seller_groups(items, pincode)
    shipping_amount = sum((seller['shipping_preview'] for seller in checkout_sellers), Decimal('0.00'))

    if request.method == 'POST' and request.POST.get('action') == 'estimate_delivery':
        submitted_pincode = request.POST.get('pincode', '').strip()
        if not re.fullmatch(r'[1-9][0-9]{5}', submitted_pincode):
            messages.error(request, 'Enter a valid 6-digit Indian PIN code.')
        else:
            request.session['delivery_pincode'] = submitted_pincode
            messages.success(request, 'Delivery fee updated for your PIN code.')
        return redirect('checkout')

    if request.method == 'POST':
        payment_method_choice = request.POST.get('payment_method', 'cod')
        if payment_method_choice not in ('cod', 'razorpay'):
            messages.error(request, 'Choose a valid payment method.')
            return redirect('checkout')
        if payment_method_choice == 'razorpay' and not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
            messages.error(request, 'Online payments are not configured yet. Please choose Cash on Delivery.')
            return redirect('checkout')

        pincode = request.POST.get('pincode', '').strip()
        if not re.fullmatch(r'[1-9][0-9]{5}', pincode):
            messages.error(request, 'Enter a valid 6-digit Indian PIN code before placing the order.')
            return redirect('checkout')
        request.session['delivery_pincode'] = pincode
        with transaction.atomic():
            locked_items = list(
                CartItem.objects.select_for_update()
                .filter(user=request.user)
                .select_related('product__shop', 'variant')
            )
            for item in locked_items:
                if not item.product.is_active or (item.product.shop_id and item.product.shop.status != 'approved'):
                    messages.error(request, f'{item.product.name} is no longer available in the Jaunpur catalog.')
                    return redirect('cart')
                stock_owner = item.variant if item.variant_id else item.product
                if item.quantity > stock_owner.stock:
                    messages.error(request, f'{item.product.name} no longer has enough stock for your cart.')
                    return redirect('cart')

            locked_subtotal = sum(
                (item.variant.final_price(pincode=pincode) if item.variant_id else item.product.final_price(pincode=pincode)) * item.quantity
                for item in locked_items
            )
            locked_coupon = Coupon.objects.select_for_update().filter(code__iexact=coupon_code).first() if coupon_code else None
            if locked_coupon and locked_coupon.is_valid_for(locked_subtotal, user=request.user):
                locked_discount = locked_coupon.discount_for(locked_subtotal)
            else:
                locked_coupon = None
                locked_discount = 0
            locked_fulfillment, locked_shipping, fulfillment_error = resolve_checkout_fulfillment(
                locked_items,
                pincode,
                request.POST,
            )
            if fulfillment_error:
                messages.error(request, fulfillment_error)
                return redirect('checkout')

            order = Order.objects.create(
                user=request.user,
                full_name=request.POST.get('full_name'),
                mobile=request.POST.get('mobile'),
                address=request.POST.get('address'),
                delivery_pincode=pincode,
                shipping_amount=locked_shipping,
                total_amount=locked_subtotal - locked_discount + locked_shipping,
                discount_amount=locked_discount,
                coupon_code=locked_coupon.code if locked_coupon else '',
                payment_method='Razorpay' if payment_method_choice == 'razorpay' else 'Cash on Delivery',
                payment_status='pending' if payment_method_choice == 'razorpay' else 'unpaid',
            )
            OrderTrackingEvent.objects.create(
                order=order,
                status=order.status,
                note='Order placed',
                created_by=request.user,
            )

            seller_orders = {}
            for item in locked_items:
                unit_price = item.variant.final_price(pincode=pincode) if item.variant_id else item.product.final_price(pincode=pincode)
                seller_order_key = item.product.shop_id
                if seller_order_key not in seller_orders:
                    fulfillment = locked_fulfillment[seller_order_key]
                    seller_orders[seller_order_key] = SellerOrder.objects.create(
                        order=order,
                        shop_id=seller_order_key,
                        subtotal=Decimal('0.00'),
                        shipping_amount=fulfillment['shipping'],
                        fulfillment_method=fulfillment['method'],
                        fulfillment_date=fulfillment['date'],
                        fulfillment_slot=fulfillment['slot'],
                    )
                seller_order = seller_orders[seller_order_key]
                seller_order.subtotal += unit_price * item.quantity
                seller_order.save(update_fields=['subtotal'])
                OrderItem.objects.create(
                    order=order,
                    seller_order=seller_order,
                    product_name=item.product.name,
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                    price=unit_price,
                    product=item.product,
                    variant=item.variant,
                    used_variant=bool(item.variant_id),
                )

                stock_owner = item.variant if item.variant_id else item.product
                stock_owner.stock -= item.quantity
                stock_owner.save(update_fields=['stock'])

            seller_order_rows = list(seller_orders.values())
            remaining_discount = Decimal(locked_discount)
            for index, seller_order in enumerate(seller_order_rows):
                if index == len(seller_order_rows) - 1:
                    seller_discount = remaining_discount
                elif locked_subtotal:
                    seller_discount = (Decimal(locked_discount) * seller_order.subtotal / locked_subtotal).quantize(Decimal('0.01'))
                    seller_discount = min(seller_discount, remaining_discount)
                else:
                    seller_discount = Decimal('0.00')
                remaining_discount -= seller_discount
                seller_order.sales_amount = max(Decimal('0.00'), seller_order.subtotal - seller_discount)
                seller_order.commission_rate = seller_order.shop.commission_rate if seller_order.shop_id else Decimal('0.00')
                seller_order.commission_amount = (
                    seller_order.sales_amount * seller_order.commission_rate / Decimal('100')
                ).quantize(Decimal('0.01'))
                seller_order.net_amount = seller_order.sales_amount - seller_order.commission_amount
                seller_order.save(update_fields=[
                    'sales_amount', 'commission_rate', 'commission_amount', 'net_amount'
                ])

            if locked_coupon and payment_method_choice == 'cod':
                locked_coupon.used_count += 1
                locked_coupon.save(update_fields=['used_count'])
                ReferralReward.objects.filter(
                    reward_coupon_code=locked_coupon.code,
                    status='earned',
                ).update(status='redeemed')

            if payment_method_choice == 'cod':
                CartItem.objects.filter(user=request.user).delete()

        if payment_method_choice == 'cod':
            request.session.pop('coupon_code', None)
            request.session.pop('delivery_pincode', None)
            transaction.on_commit(lambda order_id=order.pk: send_order_confirmation(order_id))
            return redirect('my_orders')

        attempt = PaymentAttempt.objects.create(
            order=order,
            amount_subunits=int((order.total_amount * Decimal('100')).quantize(Decimal('1'))),
            currency='INR',
        )
        try:
            attempt.gateway_order_id = create_razorpay_order(
                attempt,
                receipt=f'shop{order.pk}{uuid.uuid4().hex[:24]}',
            )
            attempt.save(update_fields=['gateway_order_id'])
        except (PaymentGatewayError, KeyError):
            with transaction.atomic():
                failed_order = Order.objects.select_for_update().get(pk=order.pk)
                release_order_inventory(failed_order)
                failed_order.status = 'cancelled'
                failed_order.payment_status = 'failed'
                failed_order.save(update_fields=['status', 'payment_status'])
                attempt.status = 'failed'
                attempt.save(update_fields=['status'])
                OrderTrackingEvent.objects.create(
                    order=failed_order,
                    status='cancelled',
                    note='Online payment could not be started',
                    created_by=request.user,
                )
            messages.error(request, 'The payment provider could not start checkout. Your stock has been released; try again.')
            return redirect('checkout')

        return render(request, 'orders/payment.html', {
            'order': order,
            'attempt': attempt,
            'key_id': settings.RAZORPAY_KEY_ID,
        })

    return render(request, 'orders/checkout.html', {
        'items': items,
        'total': total,
        'discount': discount,
        'grand_total': total - discount + shipping_amount,
        'coupon_code': coupon_code,
        'pincode': pincode,
        'shipping_amount': shipping_amount,
        'base_total': total - discount,
        'checkout_sellers': checkout_sellers,
        'tomorrow': (timezone.localdate() + timedelta(days=1)).isoformat(),
        'today': timezone.localdate().isoformat(),
    })


@login_required
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        subtotal = sum(
            item.total_price(pincode=request.session.get('delivery_pincode', ''))
            for item in CartItem.objects.filter(user=request.user).select_related('product', 'variant')
        )
        coupon = Coupon.objects.filter(code__iexact=code).first()
        if coupon and coupon.is_valid_for(subtotal, user=request.user):
            request.session['coupon_code'] = coupon.code
            messages.success(request, f'Coupon {coupon.code} was applied.')
        else:
            request.session.pop('coupon_code', None)
            messages.error(request, 'This coupon is invalid or does not apply to your cart.')
    return redirect('checkout')


@login_required
def verify_razorpay_payment(request):
    if request.method != 'POST':
        return redirect('my_orders')
    gateway_order_id = request.POST.get('razorpay_order_id', '')
    payment_id = request.POST.get('razorpay_payment_id', '')
    signature = request.POST.get('razorpay_signature', '')
    attempt = get_object_or_404(
        PaymentAttempt,
        gateway_order_id=gateway_order_id,
        order__user=request.user,
    )
    if attempt.status == 'paid':
        return redirect('my_orders')
    if attempt.status != 'created':
        messages.error(request, 'This payment attempt is no longer active.')
        return redirect('my_orders')
    if not verify_razorpay_signature(attempt.gateway_order_id, payment_id, signature):
        messages.error(request, 'We could not verify this payment response.')
        return redirect('my_orders')

    try:
        payment = fetch_razorpay_payment(payment_id)
    except PaymentGatewayError:
        messages.error(request, 'Payment status could not be checked. Contact the shop before placing a duplicate order.')
        return redirect('my_orders')

    if (
        payment.get('order_id') != attempt.gateway_order_id
        or payment.get('amount') != attempt.amount_subunits
        or payment.get('currency') != attempt.currency
        or payment.get('status') != 'captured'
    ):
        messages.error(request, 'The payment is not captured yet. Your order remains pending.')
        return redirect('my_orders')

    with transaction.atomic():
        attempt = PaymentAttempt.objects.select_for_update().select_related('order').get(pk=attempt.pk)
        if attempt.status == 'paid':
            return redirect('my_orders')
        if attempt.status != 'created':
            messages.error(request, 'This payment attempt is no longer active.')
            return redirect('my_orders')
        order = Order.objects.select_for_update().get(pk=attempt.order_id)
        if order.stock_released:
            messages.error(request, 'The order reservation expired. Contact the shop before making another payment.')
            return redirect('my_orders')
        attempt.status = 'paid'
        attempt.gateway_payment_id = payment_id
        attempt.paid_at = timezone.now()
        attempt.save(update_fields=['status', 'gateway_payment_id', 'paid_at'])
        order.payment_status = 'paid'
        order.status = 'confirmed'
        order.save(update_fields=['payment_status', 'status'])
        OrderTrackingEvent.objects.create(
            order=order,
            status='confirmed',
            note='Payment captured; order confirmed',
            created_by=request.user,
        )
        if order.coupon_code:
            Coupon.objects.filter(code=order.coupon_code).update(used_count=F('used_count') + 1)
            ReferralReward.objects.filter(reward_coupon_code=order.coupon_code, status='earned').update(status='redeemed')
        CartItem.objects.filter(user=request.user).delete()

    request.session.pop('coupon_code', None)
    request.session.pop('delivery_pincode', None)
    transaction.on_commit(lambda order_id=order.pk: send_order_confirmation(order_id))
    messages.success(request, 'Payment received and your order is confirmed.')
    return redirect('my_orders')


@login_required
def fail_razorpay_payment(request, attempt_id):
    if request.method == 'POST':
        with transaction.atomic():
            attempt = get_object_or_404(
                PaymentAttempt.objects.select_for_update().select_related('order'),
                pk=attempt_id,
                order__user=request.user,
            )
            if attempt.status == 'created':
                order = Order.objects.select_for_update().get(pk=attempt.order_id)
                attempt.status = 'failed'
                attempt.save(update_fields=['status'])
                order.status = 'cancelled'
                order.payment_status = 'failed'
                release_order_inventory(order)
                order.save(update_fields=['status', 'payment_status'])
                OrderTrackingEvent.objects.create(
                    order=order,
                    status='cancelled',
                    note='Online payment was not completed',
                    created_by=request.user,
                )
    messages.info(request, 'Payment was not completed. Your cart is still available for another attempt.')
    return redirect('my_orders')


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'tracking_events', 'return_requests', 'payment_attempts', 'seller_orders__shop', 'seller_orders__items',
        'seller_orders__delivery_assignment__run__rider__user',
    ).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def resume_razorpay_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user, payment_status='pending')
    attempt = order.payment_attempts.filter(status='created', gateway_order_id__isnull=False).first()
    if not attempt:
        messages.error(request, 'There is no active payment attempt for this order.')
        return redirect('my_orders')
    return render(request, 'orders/payment.html', {
        'order': order,
        'attempt': attempt,
        'key_id': settings.RAZORPAY_KEY_ID,
    })


@login_required
def request_return(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return_window = timedelta(days=getattr(settings, 'RETURN_WINDOW_DAYS', 7))
    delivered_event = order.tracking_events.filter(status='delivered').order_by('-created_at').first()
    delivered_at = delivered_event.created_at if delivered_event else order.created_at
    if order.status != 'delivered' or timezone.now() - delivered_at > return_window:
        messages.error(request, 'Returns and exchanges are available for delivered orders within 7 days.')
        return redirect('my_orders')

    if request.method == 'POST':
        request_type = request.POST.get('request_type')
        reason = request.POST.get('reason', '').strip()
        try:
            item_id = int(request.POST.get('order_item', ''))
        except (TypeError, ValueError):
            item_id = 0
        order_item = OrderItem.objects.filter(pk=item_id, order=order).select_related('product').first()
        exchange_size = request.POST.get('exchange_size', '').strip()
        if request_type not in dict(ReturnRequest.REQUEST_TYPES) or not reason or not order_item:
            messages.error(request, 'Choose one item, return or exchange, and enter a reason.')
            return render(request, 'orders/request_return.html', {'order': order})
        if request_type == 'exchange':
            if not order_item.product_id:
                messages.error(request, 'This item no longer has a catalog listing for size exchange.')
                return render(request, 'orders/request_return.html', {'order': order})
            if order_item.product.variants.filter(is_active=True).exists():
                available_sizes = set(order_item.product.variants.filter(is_active=True, stock__gt=0).values_list('size', flat=True))
            else:
                available_sizes = {size.strip() for size in order_item.product.available_sizes.split(',') if size.strip()}
            if not exchange_size or exchange_size not in available_sizes:
                messages.error(request, 'Choose a size listed as available for this shoe.')
                return render(request, 'orders/request_return.html', {'order': order})

        duplicate = ReturnRequest.objects.filter(
            customer=request.user,
            order=order,
            order_item=order_item,
            status__in=['pending', 'approved', 'received'],
        ).exists()
        if duplicate:
            messages.error(request, 'There is already an open request for this item.')
            return redirect('my_orders')

        ReturnRequest.objects.create(
            customer=request.user,
            order=order,
            order_item=order_item,
            request_type=request_type,
            exchange_size=exchange_size if request_type == 'exchange' else '',
            reason=reason,
            pickup_required=request.POST.get('pickup_required') == 'on',
            refund_status='pending' if order.payment_status == 'paid' and request_type == 'return' else 'not_applicable',
        )
        messages.success(request, 'Your return or exchange request was sent to the shop.')
        return redirect('my_orders')

    return render(request, 'orders/request_return.html', {'order': order})


@login_required
def rider_deliveries(request):
    rider = get_object_or_404(DeliveryRider, user=request.user, is_active=True)
    assignments = DeliveryAssignment.objects.filter(run__rider=rider).select_related(
        'run', 'seller_order__order', 'seller_order__shop'
    ).prefetch_related('seller_order__items').order_by('run__delivery_date', 'run__pincode', 'sequence')
    if request.method == 'POST':
        try:
            assignment_id = int(request.POST.get('assignment_id', ''))
        except (TypeError, ValueError):
            assignment_id = 0
        assignment = get_object_or_404(assignments, pk=assignment_id)
        action = request.POST.get('action')
        if assignment.status == 'delivered':
            messages.info(request, 'This delivery stop is already marked delivered.')
        elif action == 'delivered':
            delivered_to = request.POST.get('delivered_to', '').strip()
            proof_photo = request.FILES.get('proof_photo')
            invalid_photo = bool(proof_photo and proof_photo.size > 5 * 1024 * 1024)
            if proof_photo and not invalid_photo:
                try:
                    from PIL import Image

                    proof_photo.seek(0)
                    with Image.open(proof_photo) as opened_photo:
                        opened_photo.verify()
                    proof_photo.seek(0)
                except (OSError, ValueError):
                    invalid_photo = True
            if not delivered_to:
                messages.error(request, 'Enter who received the order to confirm delivery.')
            elif invalid_photo:
                messages.error(request, 'Choose a valid proof photo under 5 MB.')
            else:
                with transaction.atomic():
                    assignment.status = 'delivered'
                    assignment.delivered_to = delivered_to[:120]
                    assignment.note = request.POST.get('note', '').strip()
                    assignment.delivered_at = timezone.now()
                    if proof_photo:
                        assignment.proof_photo = proof_photo
                    assignment.save(update_fields=['status', 'delivered_to', 'note', 'delivered_at', 'proof_photo'])
                    seller_order = assignment.seller_order
                    seller_order.status = 'delivered'
                    seller_order.save(update_fields=['status'])
                    order = seller_order.order
                    remaining = order.seller_orders.exclude(status='delivered').exists()
                    order.status = 'out_for_delivery' if remaining else 'delivered'
                    order.save(update_fields=['status'])
                    if not remaining:
                        award_loyalty_for_order(order)
                    OrderTrackingEvent.objects.create(
                        order=order,
                        status=order.status,
                        note=f'{seller_order.shop.name if seller_order.shop_id else "Jaunpur Footwear"}: delivered to {delivered_to}.',
                        created_by=request.user,
                    )
                    transaction.on_commit(lambda order_id=order.pk: send_order_status_update(order_id))
                    if not assignment.run.assignments.exclude(status='delivered').exists():
                        assignment.run.status = 'completed'
                        assignment.run.save(update_fields=['status'])
                messages.success(request, f'Order #{seller_order.order_id} delivery recorded.')
        elif action == 'failed':
            note = request.POST.get('note', '').strip()
            if not note:
                messages.error(request, 'Add a short note about the failed delivery attempt.')
            else:
                assignment.note = note
                assignment.save(update_fields=['note'])
                messages.warning(request, 'Attempt recorded. This stop remains on your route for retry.')
        return redirect('rider_deliveries')
    return render(request, 'orders/rider_deliveries.html', {'rider': rider, 'assignments': assignments})
