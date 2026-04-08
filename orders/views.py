from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from products.models import Product
from .models import CartItem, Order, OrderItem


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        size = request.POST.get('size')
        quantity = int(request.POST.get('quantity', 1))

        item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            size=size
        )

        if not created:
            item.quantity += quantity
        else:
            item.quantity = quantity

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

    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            full_name=request.POST.get('full_name'),
            mobile=request.POST.get('mobile'),
            address=request.POST.get('address'),
            total_amount=total,
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                product_name=item.product.name,
                size=item.size,
                quantity=item.quantity,
                price=item.product.final_price()
            )

            item.product.stock -= item.quantity
            item.product.save()

        items.delete()

        return redirect('my_orders')

    return render(request, 'orders/checkout.html', {
        'items': items,
        'total': total,
    })


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})