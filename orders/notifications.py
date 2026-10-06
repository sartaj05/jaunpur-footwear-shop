import json
import logging
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mail

from accounts.models import CustomerProfile
from .models import Order

logger = logging.getLogger(__name__)


def send_whatsapp_template(phone, template_name, body_parameters, language_code='en_US'):
    if not all((
        settings.WHATSAPP_GRAPH_API_VERSION,
        settings.WHATSAPP_PHONE_NUMBER_ID,
        settings.WHATSAPP_ACCESS_TOKEN,
        template_name,
    )):
        return False
    digits = re.sub(r'\D', '', phone or '')
    if len(digits) == 10:
        digits = f'91{digits}'
    if len(digits) != 12 or not digits.startswith('91'):
        return False
    payload = {
        'messaging_product': 'whatsapp',
        'to': digits,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': language_code},
            'components': [{
                'type': 'body',
                'parameters': [{'type': 'text', 'text': str(value)[:500]} for value in body_parameters],
            }],
        },
    }
    version = settings.WHATSAPP_GRAPH_API_VERSION.strip('/')
    if not re.fullmatch(r'v\d+\.\d+', version):
        return False
    url = f'https://graph.facebook.com/{version}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages'
    request = Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        logger.warning('WhatsApp template delivery failed for the configured Jaunpur order sender.')
        return False


def _send_order_whatsapp(order, profile):
    if not profile or not profile.whatsapp_order_updates:
        return
    language = 'hi' if profile.preferred_language == 'hi' else 'en_US'
    send_whatsapp_template(
        order.mobile or profile.mobile,
        settings.WHATSAPP_ORDER_TEMPLATE,
        [order.pk, order.full_name, order.get_status_display()],
        language_code=language,
    )


def send_order_confirmation(order_id):
    order = Order.objects.select_related('user').prefetch_related('items').filter(pk=order_id).first()
    if not order:
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
    if order.user.email:
        send_mail(
            f'Order #{order.pk} received',
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            fail_silently=True,
        )
    _send_order_whatsapp(order, CustomerProfile.objects.filter(user_id=order.user_id).first())


def send_order_status_update(order_id):
    order = Order.objects.select_related('user').filter(pk=order_id).first()
    if not order:
        return

    if order.user.email:
        send_mail(
            f'Order #{order.pk} update',
            f'Your order #{order.pk} is now {order.get_status_display()}.',
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            fail_silently=True,
        )
    _send_order_whatsapp(order, CustomerProfile.objects.filter(user_id=order.user_id).first())
