import base64
import json
import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timezone as datetime_timezone

from products.models import Product, ProductVariant

from .inventory import marketplace_reserved_quantity
from .marketplace_auth import (
    MarketplaceAuthorizationError,
    decrypt_marketplace_token,
    encrypt_marketplace_token,
)
from .models import (
    MarketplaceChannelOrder,
    MarketplaceChannelOrderItem,
    MarketplaceConnection,
    MarketplaceProductMapping,
    MarketplaceSyncRun,
)


class MarketplaceSyncError(Exception):
    """Safe error message for a marketplace sync run."""


def _api_json(url, method, access_token, provider, body=None, extra_headers=None):
    headers = {'Accept': 'application/json'}
    if provider == 'flipkart':
        headers['Authorization'] = f'Bearer {access_token}'
    else:
        headers['x-amz-access-token'] = access_token
        headers['user-agent'] = settings.MARKETPLACE_API_USER_AGENT
    if body is not None:
        headers['Content-Type'] = 'application/json; charset=utf-8'
    if extra_headers:
        headers.update(extra_headers)
    payload = json.dumps(body).encode('utf-8') if body is not None else None
    request = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            content = response.read(5 * 1024 * 1024 + 1)
            if len(content) > 5 * 1024 * 1024:
                raise MarketplaceSyncError('Marketplace response exceeded the 5 MB safety limit.')
            if not content:
                return {}
            data = json.loads(content.decode('utf-8'))
            if not isinstance(data, dict):
                raise MarketplaceSyncError('Marketplace returned an unexpected response format.')
            return data
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise MarketplaceAuthorizationError(f'{provider.title()} rejected seller authorization ({exc.code}).') from None
        raise MarketplaceSyncError(f'{provider.title()} API request failed ({exc.code}).') from None
    except (URLError, TimeoutError, OSError):
        raise MarketplaceSyncError(f'{provider.title()} API could not be reached. Try again later.') from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise MarketplaceSyncError(f'{provider.title()} returned invalid JSON.') from None


def _save_access_tokens(connection, token_data, provider):
    access_token = token_data.get('access_token')
    if not access_token:
        raise MarketplaceAuthorizationError(f'{provider.title()} did not return an access token.')
    connection.encrypted_access_token = encrypt_marketplace_token(access_token)
    rotated_refresh = token_data.get('refresh_token')
    if rotated_refresh:
        connection.encrypted_refresh_token = encrypt_marketplace_token(rotated_refresh)
    expires_in = max(0, int(token_data.get('expires_in', 0)))
    connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in) if expires_in else None
    refresh_expires_in = token_data.get('refresh_token_expires_in')
    if refresh_expires_in:
        connection.refresh_token_expires_at = timezone.now() + timedelta(seconds=max(0, int(refresh_expires_in)))
    connection.authorization_status = 'connected'
    connection.save(update_fields=[
        'encrypted_access_token', 'encrypted_refresh_token', 'token_expires_at',
        'refresh_token_expires_at', 'authorization_status', 'updated_at',
    ])
    return access_token


def _refresh_flipkart(connection, refresh_token):
    if not all((settings.FLIPKART_CLIENT_ID, settings.FLIPKART_CLIENT_SECRET)):
        raise MarketplaceAuthorizationError('Flipkart app credentials are not configured.')
    credentials = base64.b64encode(
        f'{settings.FLIPKART_CLIENT_ID}:{settings.FLIPKART_CLIENT_SECRET}'.encode('utf-8')
    ).decode('ascii')
    query = urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh_token})
    separator = '&' if '?' in settings.FLIPKART_TOKEN_URL else '?'
    request = Request(
        f'{settings.FLIPKART_TOKEN_URL}{separator}{query}',
        headers={'Authorization': f'Basic {credentials}', 'Accept': 'application/json'},
        method='GET',
    )
    try:
        with urlopen(request, timeout=15) as response:
            token_data = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise MarketplaceAuthorizationError('Flipkart refresh token was rejected. Reauthorize this seller account.') from None
    return _save_access_tokens(connection, token_data, 'Flipkart')


def _refresh_amazon(connection, refresh_token):
    credentials = (settings.AMAZON_LWA_CLIENT_ID, settings.AMAZON_LWA_CLIENT_SECRET)
    if not all(credentials):
        raise MarketplaceAuthorizationError('Amazon LWA app credentials are not configured.')
    body = urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': settings.AMAZON_LWA_CLIENT_ID,
        'client_secret': settings.AMAZON_LWA_CLIENT_SECRET,
    }).encode('utf-8')
    request = Request(
        settings.AMAZON_LWA_TOKEN_URL,
        data=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(request, timeout=15) as response:
            token_data = json.loads(response.read().decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise MarketplaceAuthorizationError('Amazon refresh token was rejected. Reauthorize this seller account.') from None
    return _save_access_tokens(connection, token_data, 'Amazon')


def marketplace_access_token(connection):
    if connection.authorization_status != 'connected':
        raise MarketplaceAuthorizationError('This seller account is not authorized.')
    try:
        refresh_token = decrypt_marketplace_token(connection.encrypted_refresh_token)
        access_token = decrypt_marketplace_token(connection.encrypted_access_token)
    except MarketplaceAuthorizationError:
        raise
    if connection.refresh_token_expires_at and connection.refresh_token_expires_at <= timezone.now():
        raise MarketplaceAuthorizationError('The seller refresh token expired. Reauthorize this account.')
    if connection.token_expires_at and connection.token_expires_at <= timezone.now() + timedelta(minutes=5):
        if not refresh_token:
            raise MarketplaceAuthorizationError('The seller access token expired. Reauthorize this account.')
        if connection.channel == 'amazon':
            return _refresh_amazon(connection, refresh_token)
        return _refresh_flipkart(connection, refresh_token)
    if not access_token:
        if not refresh_token:
            raise MarketplaceAuthorizationError('The seller account has no usable API token. Reauthorize it.')
        if connection.channel == 'amazon':
            return _refresh_amazon(connection, refresh_token)
        return _refresh_flipkart(connection, refresh_token)
    return access_token


def _parse_datetime(value):
    if not value:
        return None
    parsed = parse_datetime(str(value))
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _decimal(value):
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _stock_owner(mapping):
    return mapping.variant if mapping.variant_id else mapping.product


def _sync_item_inventory(item, mapping, old_inventory_status):
    status = (item.external_status or '').upper()
    cancelled = status in {'CANCELLED', 'CANCELED', 'BUYER_CANCELLED', 'SELLER_CANCELLED'}
    shipped = status in {'SHIPPED', 'DELIVERED', 'PICKUP_COMPLETE', 'FULFILLED', 'INVOICE_UNCONFIRMED'}

    if cancelled:
        if item.consumed_quantity and old_inventory_status != 'sold' and mapping:
            with transaction.atomic():
                locked_mapping = MarketplaceProductMapping.objects.select_for_update(of=('self',)).filter(pk=mapping.pk).first()
                owner = None
                if locked_mapping:
                    if locked_mapping.variant_id:
                        owner = ProductVariant.objects.select_for_update().filter(pk=locked_mapping.variant_id).first()
                    else:
                        owner = Product.objects.select_for_update().filter(pk=locked_mapping.product_id).first()
                if owner:
                    owner.stock += item.consumed_quantity
                    owner.save(update_fields=['stock'])
                if locked_mapping and item.allocation_consumed_quantity:
                    locked_mapping.allocated_quantity += item.allocation_consumed_quantity
                    locked_mapping.save(update_fields=['allocated_quantity', 'updated_at'])
        item.consumed_quantity = 0
        item.allocation_consumed_quantity = 0
        item.allocation_processed_quantity = 0
        item.inventory_status = 'released'
        item.save(update_fields=[
            'consumed_quantity', 'allocation_consumed_quantity', 'allocation_processed_quantity',
            'inventory_status', 'updated_at',
        ])
        return

    if not mapping:
        item.inventory_status = 'unmapped'
        item.save(update_fields=['inventory_status', 'updated_at'])
        return
    with transaction.atomic():
        locked_item = MarketplaceChannelOrderItem.objects.select_for_update().get(pk=item.pk)
        locked_mapping = MarketplaceProductMapping.objects.select_for_update(of=('self',)).select_related('product', 'variant').get(pk=mapping.pk)
        owner = ProductVariant.objects.select_for_update().get(pk=locked_mapping.variant_id) if locked_mapping.variant_id else Product.objects.select_for_update().get(pk=locked_mapping.product_id)
        stock_due = max(0, locked_item.quantity - locked_item.consumed_quantity)
        allocation_due = max(0, locked_item.quantity - locked_item.allocation_processed_quantity)
        allocation_used = min(allocation_due, locked_mapping.allocated_quantity)
        if allocation_used:
            locked_mapping.allocated_quantity -= allocation_used
            locked_mapping.save(update_fields=['allocated_quantity', 'updated_at'])
            locked_item.allocation_consumed_quantity += allocation_used
        locked_item.allocation_processed_quantity += allocation_due
        applied = min(stock_due, owner.stock)
        if applied:
            owner.stock -= applied
            owner.save(update_fields=['stock'])
            locked_item.consumed_quantity += applied
        if locked_item.consumed_quantity >= locked_item.quantity:
            locked_item.inventory_status = 'sold' if shipped else 'reserved'
        else:
            locked_item.inventory_status = 'shortage'
        locked_item.save(update_fields=[
            'consumed_quantity', 'allocation_consumed_quantity', 'allocation_processed_quantity',
            'inventory_status', 'updated_at',
        ])
        item.refresh_from_db(fields=[
            'consumed_quantity', 'allocation_consumed_quantity', 'allocation_processed_quantity', 'inventory_status',
        ])


def _upsert_remote_order(connection, order_data):
    items = order_data.get('items') or []
    amount_total = sum((line.get('unit_price') or Decimal('0.00')) * line.get('quantity', 0) for line in items)
    with transaction.atomic():
        order, _ = MarketplaceChannelOrder.objects.get_or_create(
            connection=connection,
            external_order_id=order_data['external_order_id'],
            defaults={
                'marketplace_id': order_data.get('marketplace_id', ''),
                'external_status': order_data.get('status', ''),
                'purchased_at': order_data.get('purchased_at'),
                'currency': order_data.get('currency', 'INR')[:3] or 'INR',
                'total_amount': amount_total,
            },
        )
        order.marketplace_id = order_data.get('marketplace_id', '') or order.marketplace_id
        order.external_status = order_data.get('status', '')
        order.purchased_at = order_data.get('purchased_at') or order.purchased_at
        order.currency = (order_data.get('currency', 'INR') or 'INR')[:3]
        order.total_amount = amount_total
        order.save(update_fields=['marketplace_id', 'external_status', 'purchased_at', 'currency', 'total_amount', 'last_synced_at'])
        for line_data in items:
            external_item_id = str(line_data.get('external_item_id') or '')
            if not external_item_id:
                continue
            mapping = MarketplaceProductMapping.objects.filter(
                connection=connection,
                external_sku=line_data.get('external_sku', ''),
            ).select_related('product', 'variant').first()
            item, _ = MarketplaceChannelOrderItem.objects.get_or_create(
                order=order,
                external_item_id=external_item_id,
                defaults={'external_sku': line_data.get('external_sku', '')[:120]},
            )
            old_inventory_status = item.inventory_status
            item.external_sku = line_data.get('external_sku', '')[:120]
            item.mapping = mapping
            item.quantity = max(0, int(line_data.get('quantity') or 0))
            item.unit_price = line_data.get('unit_price')
            item.currency = (line_data.get('currency', order.currency) or order.currency)[:3]
            item.external_status = line_data.get('status') or order.external_status
            item.save(update_fields=[
                'external_sku', 'mapping', 'quantity', 'unit_price', 'currency', 'external_status', 'updated_at',
            ])
            _sync_item_inventory(item, mapping, old_inventory_status)
    return len(items)


def _amazon_item_price(item):
    product = item.get('product') or {}
    price = product.get('price') or {}
    value = _decimal((price.get('unitPrice') or {}).get('amount'))
    if value is not None:
        return value
    proceeds = item.get('proceeds') or {}
    total = _decimal((proceeds.get('proceedsTotal') or {}).get('amount'))
    quantity = max(1, int(item.get('quantityOrdered') or 1))
    return (total / quantity).quantize(Decimal('0.01')) if total is not None else None


def _sync_amazon_orders(connection, token):
    marketplace_ids = [value.strip() for value in connection.amazon_marketplace_ids.split(',') if value.strip()]
    if len(marketplace_ids) != 1:
        raise MarketplaceSyncError('Shared stock sync currently requires one Amazon marketplace ID per seller connection.')
    last_run = connection.sync_runs.filter(status='succeeded').order_by('-started_at').first()
    updated_after = (last_run.started_at - timedelta(minutes=5)) if last_run else (timezone.now() - timedelta(days=7))
    updated_after = updated_after.astimezone(datetime_timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    base_url = settings.AMAZON_SP_API_ENDPOINT.rstrip('/') + '/orders/2026-01-01/orders'
    pagination_token = ''
    imported_orders = 0
    imported_items = 0
    pages = 0
    while True:
        params = {
            'lastUpdatedAfter': updated_after,
            'marketplaceIds': marketplace_ids[0],
            'fulfilledBy': 'MERCHANT',
            'maxResultsPerPage': '100',
            'includedData': 'PROCEEDS,EXPENSE,CANCELLATION',
        }
        if pagination_token:
            params['paginationToken'] = pagination_token
        data = _api_json(f'{base_url}?{urlencode(params)}', 'GET', token, 'amazon')
        orders = data.get('orders') or (data.get('payload') or {}).get('orders') or []
        for raw_order in orders:
            order_id = str(raw_order.get('orderId') or '')
            if not order_id:
                continue
            raw_items = raw_order.get('orderItems') or []
            lines = []
            for raw_item in raw_items:
                product = raw_item.get('product') or {}
                quantity = max(0, int(raw_item.get('quantityOrdered') or 0))
                status = (raw_item.get('fulfillment') or {}).get('status') or raw_order.get('fulfillmentStatus', '')
                lines.append({
                    'external_item_id': raw_item.get('orderItemId'),
                    'external_sku': product.get('sellerSku', ''),
                    'quantity': quantity,
                    'unit_price': _amazon_item_price(raw_item),
                    'currency': ((product.get('price') or {}).get('unitPrice') or {}).get('currencyCode', 'INR'),
                    'status': status,
                })
            _upsert_remote_order(connection, {
                'external_order_id': order_id,
                'marketplace_id': (raw_order.get('salesChannel') or {}).get('marketplaceId', marketplace_ids[0]),
                'status': raw_order.get('fulfillmentStatus', ''),
                'purchased_at': _parse_datetime(raw_order.get('createdTime')),
                'currency': 'INR',
                'items': lines,
            })
            imported_orders += 1
            imported_items += len(lines)
        pagination = data.get('pagination') or {}
        pagination_token = data.get('nextToken') or pagination.get('nextToken') or ''
        pages += 1
        if not pagination_token:
            break
        if pages >= 100:
            raise MarketplaceSyncError('Amazon order pagination exceeded 100 pages; rerun sync to continue.')
    return imported_orders, imported_items


def _flipkart_request(connection, token, method, url, body=None):
    base = settings.FLIPKART_API_BASE_URL.rstrip('/')
    if url.startswith('https://'):
        full_url = url
    elif url.startswith('/sellers/'):
        full_url = f'{urlsplit(base).scheme}://{urlsplit(base).netloc}{url}'
    else:
        full_url = f'{base}/{url.lstrip("/")}'
    parts = urlsplit(full_url)
    base_parts = urlsplit(base)
    if parts.scheme != 'https' or parts.hostname != base_parts.hostname or not parts.path.startswith('/sellers/'):
        raise MarketplaceSyncError('Flipkart returned an unsupported pagination URL.')
    return _api_json(full_url, method, token, 'flipkart', body=body)


def _flipkart_search_shipments(connection, token, shipment_type, states, since):
    body = {
        'filter': {
            'type': shipment_type,
            'states': states,
            'orderDate': {'from': since.isoformat(), 'to': timezone.now().isoformat()},
        },
        'pagination': {'pageSize': 20},
    }
    data = _flipkart_request(connection, token, 'POST', 'v3/shipments/filter/', body)
    all_shipments = []
    pages = 0
    while True:
        all_shipments.extend(data.get('shipments') or [])
        next_url = data.get('nextPageUrl') or data.get('nextPageURL') or ''
        pages += 1
        if not next_url:
            return all_shipments
        if pages >= 50:
            raise MarketplaceSyncError('Flipkart shipment pagination exceeded 50 pages; rerun sync to continue.')
        data = _flipkart_request(connection, token, 'GET', next_url)


def _sync_flipkart_orders(connection, token):
    last_run = connection.sync_runs.filter(status='succeeded').order_by('-started_at').first()
    since = last_run.started_at - timedelta(minutes=5) if last_run else timezone.now() - timedelta(days=30)
    shipment_groups = []
    shipment_groups.extend(_flipkart_search_shipments(
        connection, token, 'preDispatch', ['APPROVED', 'PACKING_IN_PROGRESS', 'PACKED', 'READY_TO_DISPATCH'], since,
    ))
    shipment_groups.extend(_flipkart_search_shipments(
        connection, token, 'postDispatch', ['SHIPPED', 'DELIVERED', 'PICKUP_COMPLETE'], since,
    ))
    shipment_groups.extend(_flipkart_search_shipments(
        connection, token, 'cancelled', ['CANCELLED'], since,
    ))
    grouped = {}
    for shipment in shipment_groups:
        shipment_id = str(shipment.get('shipmentId') or '')
        for index, raw_item in enumerate(shipment.get('orderItems') or []):
            order_id = str(raw_item.get('orderId') or shipment_id)
            if not order_id:
                continue
            line_id = str(raw_item.get('orderItemId') or f'{shipment_id}-{raw_item.get("sku", index)}')
            components = raw_item.get('priceComponents') or {}
            price = _decimal(components.get('customerPrice')) or _decimal(components.get('sellingPrice'))
            grouped.setdefault(order_id, []).append({
                'external_item_id': line_id,
                'external_sku': raw_item.get('sku', ''),
                'quantity': max(0, int(raw_item.get('quantity') or 0)),
                'unit_price': price,
                'currency': 'INR',
                'status': raw_item.get('status') or shipment.get('status', ''),
                'order_date': raw_item.get('orderDate'),
            })
    for order_id, lines in grouped.items():
        statuses = sorted({line['status'] for line in lines if line['status']})
        purchased = next((_parse_datetime(line.get('order_date')) for line in lines if line.get('order_date')), None)
        _upsert_remote_order(connection, {
            'external_order_id': order_id,
            'status': ', '.join(statuses),
            'purchased_at': purchased,
            'currency': 'INR',
            'items': lines,
        })
    return len(grouped), sum(len(items) for items in grouped.values())


def _stock_mappings_for(mapping):
    query = MarketplaceProductMapping.objects.select_for_update().filter(product_id=mapping.product_id, variant_id=mapping.variant_id).order_by('pk')
    return list(query)


def _clamp_allocations(mapping):
    with transaction.atomic():
        if mapping.variant_id:
            owner = ProductVariant.objects.select_for_update().get(pk=mapping.variant_id)
        else:
            owner = Product.objects.select_for_update().get(pk=mapping.product_id)
        mappings = _stock_mappings_for(mapping)
        excess = max(0, sum(row.allocated_quantity for row in mappings) - owner.stock)
        if excess:
            for row in reversed(mappings):
                reduction = min(excess, row.allocated_quantity)
                row.allocated_quantity -= reduction
                row.save(update_fields=['allocated_quantity', 'updated_at'])
                excess -= reduction
                if not excess:
                    break


def _amazon_inventory_update(connection, token, mapping):
    marketplace_id = connection.amazon_marketplace_ids.split(',')[0].strip()
    url = (
        f"{settings.AMAZON_SP_API_ENDPOINT.rstrip('/')}/listings/2021-08-01/items/"
        f"{quote(connection.seller_account_id, safe='')}/{quote(mapping.external_sku, safe='')}?"
        f"{urlencode({'marketplaceIds': marketplace_id})}"
    )
    body = {
        'productType': 'PRODUCT',
        'patches': [{
            'op': 'replace',
            'path': '/attributes/fulfillment_availability',
            'value': [{'fulfillment_channel_code': 'DEFAULT', 'quantity': mapping.allocated_quantity}],
        }],
    }
    response = _api_json(url, 'PATCH', token, 'amazon', body=body)
    issues = response.get('issues') or []
    errors = [issue for issue in issues if (issue.get('severity') or '').upper() == 'ERROR']
    if errors:
        summary = '; '.join(str(issue.get('code') or issue.get('message') or 'listing rejected') for issue in errors[:4])
        raise MarketplaceSyncError(summary[:1000])


def _flipkart_inventory_update(connection, token, mappings):
    if not connection.fulfillment_location_id:
        raise MarketplaceSyncError('Add the Flipkart fulfillment location ID before syncing inventory.')
    payload = {}
    for mapping in mappings:
        if not re.fullmatch(r'[A-Za-z0-9_-]{13,16}', mapping.external_listing_id or ''):
            raise MarketplaceSyncError(f'{mapping.external_sku}: add the valid 13 to 16 character Flipkart product ID.')
        payload[mapping.external_sku] = {
            'product_id': mapping.external_listing_id,
            'locations': [{'id': connection.fulfillment_location_id, 'inventory': mapping.allocated_quantity}],
        }
    response = _flipkart_request(connection, token, 'POST', 'listings/v3/update/inventory', payload)
    failed = []
    def inspect(value, sku=''):
        if isinstance(value, dict):
            candidate_sku = value.get('skuId') or value.get('sku') or sku
            status = str(value.get('status') or value.get('processingStatus') or '').upper()
            if candidate_sku in payload and status and status not in {'SUCCESS', 'SUCCEEDED', 'ACCEPTED', 'COMPLETED'}:
                failed.append((candidate_sku, value.get('errorMessage') or value.get('errorCode') or 'Flipkart rejected this SKU update.'))
            for key, nested in value.items():
                inspect(nested, key if key in payload else candidate_sku)
        elif isinstance(value, list):
            for nested in value:
                inspect(nested, sku)
    inspect(response)
    if failed:
        details = '; '.join(f'{sku}: {message}' for sku, message in failed[:5])
        raise MarketplaceSyncError(details[:1000])


def _sync_inventory(connection, token):
    mappings = list(MarketplaceProductMapping.objects.filter(
        connection=connection,
        product__is_active=True,
    ).select_related('product', 'variant'))
    successful = 0
    errors = []
    for mapping in mappings:
        _clamp_allocations(mapping)
    if connection.channel == 'flipkart':
        for start in range(0, len(mappings), 10):
            batch = mappings[start:start + 10]
            try:
                _flipkart_inventory_update(connection, token, batch)
            except MarketplaceSyncError as exc:
                for mapping in batch:
                    mapping.status = 'needs_attention'
                    mapping.error_text = str(exc)[:1000]
                    mapping.save(update_fields=['status', 'error_text', 'updated_at'])
                errors.append(str(exc))
                continue
            for mapping in batch:
                mapping.status = 'submitted'
                mapping.error_text = ''
                mapping.last_synced_at = timezone.now()
                mapping.save(update_fields=['status', 'error_text', 'last_synced_at', 'updated_at'])
                successful += 1
    else:
        for mapping in mappings:
            try:
                _amazon_inventory_update(connection, token, mapping)
            except MarketplaceSyncError as exc:
                mapping.status = 'needs_attention'
                mapping.error_text = str(exc)[:1000]
                mapping.save(update_fields=['status', 'error_text', 'updated_at'])
                errors.append(str(exc))
                continue
            mapping.status = 'submitted'
            mapping.error_text = ''
            mapping.last_synced_at = timezone.now()
            mapping.save(update_fields=['status', 'error_text', 'last_synced_at', 'updated_at'])
            successful += 1
    return successful, errors


def sync_marketplace_connection(connection):
    connection = MarketplaceConnection.objects.select_related('shop').get(pk=connection.pk)
    run = MarketplaceSyncRun.objects.create(connection=connection)
    try:
        if connection.status != 'approved' or connection.authorization_status != 'connected':
            raise MarketplaceAuthorizationError('Only approved and seller-authorized channels can sync.')
        token = marketplace_access_token(connection)
        if connection.channel == 'amazon':
            order_count, line_count = _sync_amazon_orders(connection, token)
        else:
            order_count, line_count = _sync_flipkart_orders(connection, token)
        update_count, update_errors = _sync_inventory(connection, token)
        run.status = 'succeeded'
        run.orders_seen = order_count
        run.order_items_seen = line_count
        run.inventory_updates = update_count
        run.error_summary = '\n'.join(update_errors[:10])
    except (MarketplaceAuthorizationError, MarketplaceSyncError) as exc:
        run.status = 'failed'
        run.error_summary = str(exc)[:2000]
        if isinstance(exc, MarketplaceAuthorizationError):
            connection.authorization_status = 'reauthorization_required'
            connection.save(update_fields=['authorization_status', 'updated_at'])
    except (ValueError, TypeError, KeyError) as exc:
        run.status = 'failed'
        run.error_summary = f'Marketplace response could not be processed ({exc.__class__.__name__}).'
    run.completed_at = timezone.now()
    run.save(update_fields=[
        'status', 'orders_seen', 'order_items_seen', 'inventory_updates', 'error_summary', 'completed_at',
    ])
    return run
