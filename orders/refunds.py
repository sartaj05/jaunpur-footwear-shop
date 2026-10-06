from decimal import Decimal

from django.db import transaction

from .models import Order, PaymentAttempt, ReturnRefundAttempt, ReturnRequest
from .payments import PaymentGatewayError, create_razorpay_refund
from products.models import Product, ProductVariant


def process_return_refund(return_request_id):
    with transaction.atomic():
        return_request = ReturnRequest.objects.select_for_update(of=('self',)).select_related('order', 'order_item').get(pk=return_request_id)
        if return_request.request_type != 'return' or return_request.status != 'received':
            return None
        if return_request.refund_status != 'pending' or not return_request.order_item_id:
            return None
        payment_attempt = PaymentAttempt.objects.select_for_update().filter(
            order=return_request.order,
            status='paid',
            gateway_payment_id__gt='',
        ).first()
        if not payment_attempt:
            return None
        amount = (return_request.order_item.price * return_request.order_item.quantity * Decimal('100')).quantize(Decimal('1'))
        amount_subunits = int(amount)
        refund_attempt, _created = ReturnRefundAttempt.objects.get_or_create(
            return_request=return_request,
            defaults={'amount_subunits': amount_subunits},
        )
        refund_attempt = ReturnRefundAttempt.objects.select_for_update().get(pk=refund_attempt.pk)
        if refund_attempt.status != 'queued':
            return refund_attempt
        refund_attempt.status = 'processing'
        refund_attempt.save(update_fields=['status', 'updated_at'])
        payment_id = payment_attempt.gateway_payment_id

    try:
        provider_result = create_razorpay_refund(payment_id, amount_subunits, return_request_id)
    except PaymentGatewayError as exc:
        with transaction.atomic():
            refund_attempt = ReturnRefundAttempt.objects.select_for_update().get(pk=refund_attempt.pk)
            refund_attempt.status = 'review_required'
            refund_attempt.error_summary = str(exc)[:300]
            refund_attempt.save(update_fields=['status', 'error_summary', 'updated_at'])
        return refund_attempt

    if not isinstance(provider_result, dict):
        provider_result = {}
    provider_id = provider_result.get('id', '')
    try:
        provider_amount = int(provider_result.get('amount', -1))
    except (TypeError, ValueError):
        provider_amount = -1
    if not provider_id or provider_result.get('payment_id') != payment_id or provider_amount != amount_subunits:
        with transaction.atomic():
            refund_attempt = ReturnRefundAttempt.objects.select_for_update().get(pk=refund_attempt.pk)
            refund_attempt.status = 'review_required'
            refund_attempt.error_summary = 'Provider refund response did not match the submitted payment and amount.'
            refund_attempt.save(update_fields=['status', 'error_summary', 'updated_at'])
        return refund_attempt

    with transaction.atomic():
        refund_attempt = ReturnRefundAttempt.objects.select_for_update().get(pk=refund_attempt.pk)
        return_request = ReturnRequest.objects.select_for_update().get(pk=return_request_id)
        if refund_attempt.status != 'processing':
            return refund_attempt
        refund_attempt.status = 'submitted'
        refund_attempt.provider_refund_id = str(provider_id)
        refund_attempt.error_summary = ''
        refund_attempt.save(update_fields=['status', 'provider_refund_id', 'error_summary', 'updated_at'])
        return_request.refund_status = 'processed'
        return_request.refund_reference = str(provider_id)
        return_request.status = 'completed'
        return_request.save(update_fields=['refund_status', 'refund_reference', 'status', 'updated_at'])
        item = return_request.order_item
        if item and item.product_id:
            if item.used_variant and item.variant_id:
                stock_owner = ProductVariant.objects.select_for_update().filter(pk=item.variant_id).first()
                if stock_owner:
                    stock_owner._stock_change_reason = 'customer_return'
                    stock_owner._stock_change_reference = f'return:{return_request.pk}'
            elif item.used_variant:
                stock_owner, _ = ProductVariant.objects.select_for_update().get_or_create(
                    product_id=item.product_id,
                    size=item.size,
                    color=item.color,
                )
                stock_owner._stock_change_reason = 'customer_return'
                stock_owner._stock_change_reference = f'return:{return_request.pk}'
            else:
                stock_owner = Product.objects.select_for_update().filter(pk=item.product_id).first()
                if stock_owner:
                    stock_owner._stock_change_reason = 'customer_return'
                    stock_owner._stock_change_reference = f'return:{return_request.pk}'
            if stock_owner:
                stock_owner.stock += item.quantity
                stock_owner.save(update_fields=['stock'])
    return refund_attempt
