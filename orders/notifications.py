import json
import logging
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import CustomerProfile
from .models import NotificationDelivery, Order

logger = logging.getLogger(__name__)

_HINDI_ORDER_STATUS = {
    'pending': 'लंबित', 'confirmed': 'पुष्टि की गई', 'packed': 'पैक किया गया',
    'shipped': 'भेज दिया गया', 'out_for_delivery': 'डिलीवरी के लिए निकला',
    'delivered': 'डिलीवर हो गया', 'cancelled': 'रद्द',
}


def _record_channel_delivery(order, event_type, channel, summary, enabled, send_message):
    state_suffix = order.status if event_type == 'order_status' else 'placed'
    idempotency_key = f'order-{order.pk}:{event_type}:{state_suffix}:{channel}'
    existing = NotificationDelivery.objects.filter(idempotency_key=idempotency_key).first()
    if existing and existing.status == 'accepted':
        return True
    status = 'skipped'
    error_summary = ''
    accepted_at = None
    if enabled:
        try:
            accepted = bool(send_message())
        except Exception:
            logger.exception('Notification provider raised an error for order %s through %s.', order.pk, channel)
            accepted = False
        if accepted:
            status = 'accepted'
            accepted_at = timezone.now()
        else:
            status = 'failed'
            error_summary = 'The configured provider did not accept this message.'
    NotificationDelivery.objects.update_or_create(
        idempotency_key=idempotency_key,
        defaults={
            'user_id': order.user_id,
            'order': order,
            'channel': channel,
            'event_type': event_type,
            'status': status,
            'summary': summary[:240],
            'error_summary': error_summary,
            'accepted_at': accepted_at,
        },
    )
    return status in {'accepted', 'skipped'}


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


def _send_order_whatsapp(order, profile, event_type, summary):
    provider_configured = all((
        settings.WHATSAPP_GRAPH_API_VERSION,
        settings.WHATSAPP_PHONE_NUMBER_ID,
        settings.WHATSAPP_ACCESS_TOKEN,
        settings.WHATSAPP_ORDER_TEMPLATE,
    ))
    enabled = bool(profile and profile.whatsapp_order_updates and provider_configured)
    language = 'hi' if profile and profile.preferred_language == 'hi' else 'en_US'
    status_display = _HINDI_ORDER_STATUS.get(order.status, order.get_status_display()) if language == 'hi' else order.get_status_display()
    return _record_channel_delivery(
        order,
        event_type,
        'whatsapp',
        summary,
        enabled,
        lambda: send_whatsapp_template(
            order.mobile or (profile.mobile if profile else ''),
            settings.WHATSAPP_ORDER_TEMPLATE,
            [order.pk, order.full_name, status_display],
            language_code=language,
        ),
    )


def send_order_confirmation(order_id):
    order = Order.objects.select_related('user').prefetch_related('items').filter(pk=order_id).first()
    if not order:
        return True
    profile = CustomerProfile.objects.filter(user_id=order.user_id).first()
    hindi = bool(profile and profile.preferred_language == 'hi')
    status_display = _HINDI_ORDER_STATUS.get(order.status, order.get_status_display()) if hindi else order.get_status_display()
    if hindi:
        item_lines = [f'- {item.product_name} | साइज़ {item.size} | मात्रा {item.quantity}' for item in order.items.all()]
        message = '\n'.join([
            f'नमस्ते {order.full_name},', '',
            f'आपका जौनपुर फुटवियर ऑर्डर #{order.pk} प्राप्त हुआ।', *item_lines, '',
            f'कुल: ₹{order.total_amount}', f'ऑर्डर स्थिति: {status_display}',
        ])
        subject = f'ऑर्डर #{order.pk} प्राप्त हुआ'
    else:
        item_lines = [f'- {item.product_name} | size {item.size} | quantity {item.quantity}' for item in order.items.all()]
        message = '\n'.join([
            f'Hello {order.full_name},', '',
            f'Your Jaunpur Footwear order #{order.pk} has been received.', *item_lines, '',
            f'Total: ₹{order.total_amount}', f'Current status: {status_display}',
        ])
        subject = f'Order #{order.pk} received'
    email_enabled = bool(order.user.email and (profile is None or profile.email_order_updates))
    email_delivered = _record_channel_delivery(
        order,
        'order_confirmation',
        'email',
        subject,
        email_enabled,
        lambda: send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email], fail_silently=False) == 1,
    )
    whatsapp_delivered = _send_order_whatsapp(order, profile, 'order_confirmation', subject)
    return email_delivered and whatsapp_delivered


def send_order_status_update(order_id):
    order = Order.objects.select_related('user').filter(pk=order_id).first()
    if not order:
        return True

    profile = CustomerProfile.objects.filter(user_id=order.user_id).first()
    hindi = bool(profile and profile.preferred_language == 'hi')
    status_display = _HINDI_ORDER_STATUS.get(order.status, order.get_status_display()) if hindi else order.get_status_display()
    subject = f'ऑर्डर #{order.pk} अपडेट' if hindi else f'Order #{order.pk} update'
    body = f'आपका ऑर्डर #{order.pk} अब {status_display} स्थिति में है।' if hindi else f'Your order #{order.pk} is now {status_display}.'
    email_enabled = bool(order.user.email and (profile is None or profile.email_order_updates))
    email_delivered = _record_channel_delivery(
        order,
        'order_status',
        'email',
        subject,
        email_enabled,
        lambda: send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [order.user.email], fail_silently=False) == 1,
    )
    whatsapp_delivered = _send_order_whatsapp(order, profile, 'order_status', subject)
    return email_delivered and whatsapp_delivered
