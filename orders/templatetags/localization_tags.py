from django import template

register = template.Library()

_HINDI_STATUS = {
    'pending': 'लंबित',
    'confirmed': 'पुष्टि की गई',
    'packed': 'पैक किया गया',
    'shipped': 'भेज दिया गया',
    'out_for_delivery': 'डिलीवरी के लिए निकला',
    'delivered': 'डिलीवर हो गया',
    'cancelled': 'रद्द',
    'unpaid': 'भुगतान बाकी',
    'paid': 'भुगतान प्राप्त',
    'failed': 'विफल',
    'refund_pending': 'रिफंड लंबित',
    'refunded': 'रिफंड पूरा',
    'requested': 'समीक्षा लंबित',
    'rejected': 'अस्वीकृत',
    'approved': 'स्वीकृत',
    'received': 'वापस प्राप्त',
    'completed': 'पूरा',
    'not_applicable': 'लागू नहीं',
    'processed': 'भेजा गया',
    'not_required': 'आवश्यक नहीं',
}


@register.filter
def hindi_status(value):
    return _HINDI_STATUS.get(str(value or '').lower(), value)
