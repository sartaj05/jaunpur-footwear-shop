import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class MarketplaceAuthorizationError(Exception):
    """Safe, user-facing failure while authorizing a marketplace seller."""


def _fernet():
    key = settings.MARKETPLACE_TOKEN_ENCRYPTION_KEY
    if not key:
        raise MarketplaceAuthorizationError('Marketplace token encryption is not configured.')
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, UnicodeEncodeError):
        raise MarketplaceAuthorizationError('Marketplace token encryption key is invalid.') from None


def encrypt_marketplace_token(value):
    if not value:
        return ''
    return _fernet().encrypt(value.encode('utf-8')).decode('ascii')


def decrypt_marketplace_token(value):
    if not value:
        return ''
    try:
        return _fernet().decrypt(value.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError, UnicodeEncodeError):
        raise MarketplaceAuthorizationError('Stored marketplace credentials cannot be decrypted.') from None


def marketplace_encryption_is_configured():
    try:
        _fernet()
        return True
    except MarketplaceAuthorizationError:
        return False


def exchange_flipkart_code(code):
    credentials = (settings.FLIPKART_CLIENT_ID, settings.FLIPKART_CLIENT_SECRET, settings.FLIPKART_REDIRECT_URI)
    if not all(credentials):
        raise MarketplaceAuthorizationError('Flipkart developer app credentials are not configured.')
    basic = base64.b64encode(f'{settings.FLIPKART_CLIENT_ID}:{settings.FLIPKART_CLIENT_SECRET}'.encode('utf-8')).decode('ascii')
    body = urlencode({
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.FLIPKART_REDIRECT_URI,
    }).encode('utf-8')
    request = Request(
        settings.FLIPKART_TOKEN_URL,
        data=body,
        headers={
            'Authorization': f'Basic {basic}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=15) as response:
            token_data = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise MarketplaceAuthorizationError('Flipkart could not authorize this seller account. Try again or contact support.') from None
    if not isinstance(token_data, dict) or not token_data.get('access_token'):
        raise MarketplaceAuthorizationError('Flipkart returned an incomplete authorization response.')
    return token_data
