import csv
import io
import os
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from .models import MarketplaceChannelOrder, MarketplaceSettlementImport, MarketplaceSettlementLine


REQUIRED_COLUMNS = {'external_order_id', 'marketplace_fee', 'settlement_amount', 'settlement_reference'}
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000
MAX_AMOUNT = Decimal('10000000000')


def _parse_amount(value):
    amount = Decimal(value)
    if (
        not amount.is_finite()
        or amount < 0
        or amount >= MAX_AMOUNT
        or max(0, -amount.as_tuple().exponent) > 2
    ):
        raise InvalidOperation
    return amount


def import_settlement_statement(connection, uploaded_file, user):
    filename = os.path.basename((uploaded_file.name or 'statement.csv').replace('\\', '/'))[:180]
    if not filename.lower().endswith('.csv') or uploaded_file.size > MAX_FILE_BYTES:
        raise ValueError('Choose a CSV settlement statement under 2 MB.')
    try:
        content = uploaded_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        headers = {str(field or '').strip().lower() for field in reader.fieldnames or []}
    except (UnicodeDecodeError, csv.Error, OSError):
        raise ValueError('Could not read this file. Save it as a UTF-8 CSV and try again.') from None

    batch = MarketplaceSettlementImport.objects.create(
        connection=connection,
        uploaded_by=user,
        source_filename=filename,
    )
    if not REQUIRED_COLUMNS.issubset(headers):
        batch.rows_failed = 1
        batch.error_summary = 'CSV must include external_order_id, marketplace_fee, settlement_amount, settlement_reference.'
        batch.save(update_fields=['rows_failed', 'error_summary'])
        return batch

    seen_order_ids = set()
    errors = []
    try:
        for row_number, raw_row in enumerate(reader, start=2):
            if batch.rows_seen >= MAX_ROWS:
                errors.append(f'Row {row_number}: file exceeds the {MAX_ROWS}-row limit.')
                batch.rows_failed += 1
                break
            batch.rows_seen += 1
            row = {
                str(key).strip().lower(): str(value or '').strip()
                for key, value in raw_row.items() if key is not None
            }
            external_order_id = row.get('external_order_id', '')[:160]
            reference = row.get('settlement_reference', '')[:160]
            reason = ''
            try:
                fee = _parse_amount(row.get('marketplace_fee', ''))
                settlement_amount = _parse_amount(row.get('settlement_amount', ''))
            except (InvalidOperation, TypeError, ValueError):
                fee, settlement_amount = None, None
                reason = 'Fee and settlement amount must be valid non-negative amounts with at most two decimal places.'
            if not external_order_id:
                reason = reason or 'External order ID is required.'
            elif external_order_id in seen_order_ids:
                reason = reason or 'Duplicate external order ID in this file.'
            elif not reference:
                reason = reason or 'Settlement reference is required.'
            seen_order_ids.add(external_order_id)

            order = None
            if not reason:
                order = MarketplaceChannelOrder.objects.filter(
                    connection=connection,
                    external_order_id=external_order_id,
                ).first()
                if order is None:
                    reason = 'No synchronized order matches this marketplace account and external ID.'

            with transaction.atomic():
                if reason:
                    status = 'missing_order' if 'No synchronized order' in reason else 'invalid'
                    MarketplaceSettlementLine.objects.create(
                        settlement_import=batch,
                        order=order,
                        external_order_id=external_order_id,
                        marketplace_fee=fee,
                        settlement_amount=settlement_amount,
                        settlement_reference=reference,
                        status=status,
                        error_summary=reason,
                    )
                    batch.rows_failed += 1
                    errors.append(f'Row {row_number}: {reason}')
                    continue

                order = MarketplaceChannelOrder.objects.select_for_update().get(pk=order.pk)
                order.marketplace_fee = fee
                order.settlement_amount = settlement_amount
                order.settlement_reference = reference
                order.reconciliation_status = 'reconciled'
                order.reconciled_at = timezone.now()
                order.save(update_fields=[
                    'marketplace_fee', 'settlement_amount', 'settlement_reference',
                    'reconciliation_status', 'reconciled_at', 'last_synced_at',
                ])
                MarketplaceSettlementLine.objects.create(
                    settlement_import=batch,
                    order=order,
                    external_order_id=external_order_id,
                    marketplace_fee=fee,
                    settlement_amount=settlement_amount,
                    settlement_reference=reference,
                    status='matched',
                )
                batch.rows_updated += 1
    except csv.Error:
        errors.append('The CSV contains a malformed row. Check its quoting and delimiters.')
        batch.rows_failed += 1

    batch.error_summary = '\n'.join(errors[:25])[:5000]
    batch.save(update_fields=['rows_seen', 'rows_updated', 'rows_failed', 'error_summary'])
    return batch
