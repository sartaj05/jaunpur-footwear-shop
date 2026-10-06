from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from products.models import Product, ProductVariant
from .models import CartItem, Coupon, Order, OrderItem


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
    total = sum(item.total_price() for item in items)

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
    items = CartItem.objects.filter(user=request.user)

    if not items.exists():
        return redirect('cart')

    total = sum(item.total_price() for item in items)
    coupon_code = request.session.get('coupon_code', '')
    coupon = Coupon.objects.filter(code__iexact=coupon_code).first() if coupon_code else None
    if coupon and coupon.is_valid_for(total):
        discount = coupon.discount_for(total)
    else:
        discount = 0
        if coupon_code:
            request.session.pop('coupon_code', None)
            coupon_code = ''
            messages.warning(request, 'The applied coupon is no longer valid.')

    if request.method == 'POST':
        with transaction.atomic():
            locked_items = list(
                CartItem.objects.select_for_update()
                .filter(user=request.user)
                .select_related('product', 'variant')
            )
            for item in locked_items:
                stock_owner = item.variant if item.variant_id else item.product
                if item.quantity > stock_owner.stock:
                    messages.error(request, f'{item.product.name} no longer has enough stock for your cart.')
                    return redirect('cart')

            locked_subtotal = sum(
                (item.variant.final_price() if item.variant_id else item.product.final_price()) * item.quantity
                for item in locked_items
            )
            locked_coupon = Coupon.objects.select_for_update().filter(code__iexact=coupon_code).first() if coupon_code else None
            if locked_coupon and locked_coupon.is_valid_for(locked_subtotal):
                locked_discount = locked_coupon.discount_for(locked_subtotal)
            else:
                locked_coupon = None
                locked_discount = 0

            order = Order.objects.create(
                user=request.user,
                full_name=request.POST.get('full_name'),
                mobile=request.POST.get('mobile'),
                address=request.POST.get('address'),
                total_amount=locked_subtotal - locked_discount,
                discount_amount=locked_discount,
                coupon_code=locked_coupon.code if locked_coupon else '',
            )

            for item in locked_items:
                unit_price = item.variant.final_price() if item.variant_id else item.product.final_price()
                OrderItem.objects.create(
                    order=order,
                    product_name=item.product.name,
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                    price=unit_price,
                )

                stock_owner = item.variant if item.variant_id else item.product
                stock_owner.stock -= item.quantity
                stock_owner.save(update_fields=['stock'])

            if locked_coupon:
                locked_coupon.used_count += 1
                locked_coupon.save(update_fields=['used_count'])

            CartItem.objects.filter(user=request.user).delete()

        request.session.pop('coupon_code', None)
        return redirect('my_orders')

    return render(request, 'orders/checkout.html', {
        'items': items,
        'total': total,
        'discount': discount,
        'grand_total': total - discount,
        'coupon_code': coupon_code,
    })


@login_required
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        subtotal = sum(
            item.total_price()
            for item in CartItem.objects.filter(user=request.user).select_related('product', 'variant')
        )
        coupon = Coupon.objects.filter(code__iexact=code).first()
        if coupon and coupon.is_valid_for(subtotal):
            request.session['coupon_code'] = coupon.code
            messages.success(request, f'Coupon {coupon.code} was applied.')
        else:
            request.session.pop('coupon_code', None)
            messages.error(request, 'This coupon is invalid or does not apply to your cart.')
    return redirect('checkout')


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})
