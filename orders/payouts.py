from decimal import Decimal

from django.db.models import Q

from .models import SellerOrder


def eligible_seller_orders():
    """Return delivered shop orders that can safely enter a staff payout batch."""
    return SellerOrder.objects.filter(
        status='delivered',
        payout_status='pending',
        shop__isnull=False,
    ).exclude(
        order__status='cancelled',
    ).filter(
        Q(order__payment_status='paid') | Q(order__payment_method='Cash on Delivery'),
    ).exclude(
        items__return_requests__status__in=['pending', 'approved', 'received'],
    ).exclude(
        payout_batch_items__batch__status='prepared',
    ).distinct()


def payout_return_adjustment(seller_order):
    refunded_returns = seller_order.items.filter(
        return_requests__request_type='return',
        return_requests__refund_status='processed',
    ).distinct()
    adjustment = sum(
        (item.price * item.quantity * (Decimal('100.00') - seller_order.commission_rate) / Decimal('100.00'))
        for item in refunded_returns
    )
    return min(seller_order.net_amount, adjustment).quantize(Decimal('0.01'))


def payout_snapshot(seller_order):
    adjustment = payout_return_adjustment(seller_order)
    return {
        'seller_order': seller_order,
        'sales_amount': seller_order.sales_amount,
        'commission_amount': seller_order.commission_amount,
        'return_adjustment': adjustment,
        'payout_amount': max(Decimal('0.00'), seller_order.net_amount - adjustment).quantize(Decimal('0.01')),
    }
