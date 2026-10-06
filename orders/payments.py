import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request
from decimal import Decimal

from django.conf import settings
from products.models import Product, ProductVariant


class PaymentGatewayError(Exception):
    pass


def _razorpay_request(path, method='GET', payload=None):
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    if not key_id or not key_secret:
        raise PaymentGatewayError('Razorpay keys are not configured.')

    credentials = base64.b64encode(f'{key_id}:{key_secret}'.encode()).decode()
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f'https://api.razorpay.com/v1/{path}',
        data=data,
        headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/json',
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        raise PaymentGatewayError('Razorpay could not complete the request.') from exc


def create_razorpay_order(attempt, receipt):
    amount = int((attempt.order.total_amount * Decimal('100')).quantize(Decimal('1')))
    result = _razorpay_request('orders', method='POST', payload={
        'amount': amount,
        'currency': attempt.currency,
        'receipt': receipt[:40],
        'notes': {'shop_order_id': str(attempt.order_id)},
    })
    return result['id']


def verify_razorpay_signature(order_id, payment_id, signature):
    digest = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f'{order_id}|{payment_id}'.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


def fetch_razorpay_payment(payment_id):
    return _razorpay_request(f'payments/{payment_id}')


def release_order_inventory(order):
    if order.stock_released:
        return
    for item in order.items.select_for_update():
        if item.variant_id:
            variant = ProductVariant.objects.select_for_update().filter(pk=item.variant_id).first()
            if variant:
                variant.stock += item.quantity
                variant.save(update_fields=['stock'])
        elif item.used_variant and item.product_id:
            variant, _ = ProductVariant.objects.get_or_create(
                product_id=item.product_id,
                size=item.size,
                color=item.color,
            )
            variant.stock += item.quantity
            variant.save(update_fields=['stock'])
        elif item.product_id:
            product = Product.objects.select_for_update().filter(pk=item.product_id).first()
            if product:
                product.stock += item.quantity
                product.save(update_fields=['stock'])
    order.stock_released = True
    order.save(update_fields=['stock_released'])
