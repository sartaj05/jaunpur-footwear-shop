from django.conf import settings
from django.core.mail import send_mail

from .models import Order


def send_order_confirmation(order_id):
    order = Order.objects.select_related('user').prefetch_related('items').filter(pk=order_id).first()
    if not order or not order.user.email:
        return

    item_lines = [
        f'- {item.product_name} | size {item.size} | quantity {item.quantity}'
        for item in order.items.all()
    ]
    message = '\n'.join([
        f'Hello {order.full_name},',
        '',
        f'Your Jaunpur Footwear order #{order.pk} has been received.',
        *item_lines,
        '',
        f'Total: ₹{order.total_amount}',
        f'Current status: {order.get_status_display()}',
    ])
    send_mail(
        f'Order #{order.pk} received',
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=True,
    )


def send_order_status_update(order_id):
    order = Order.objects.select_related('user').filter(pk=order_id).first()
    if not order or not order.user.email:
        return

    send_mail(
        f'Order #{order.pk} update',
        f'Your order #{order.pk} is now {order.get_status_display()}.',
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=True,
    )
