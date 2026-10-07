import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from orders.models import PaymentWebhookEvent, ReturnRefundAttempt
from .models import BackgroundJobRun, RecoveryCheck, SystemAlert

logger = logging.getLogger(__name__)


def publish_alert(dedupe_key, source, severity, title, details):
    alert, created = SystemAlert.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults={
            'source': source,
            'severity': severity,
            'title': title,
            'details': details[:4000],
        },
    )
    reopened = not created and alert.state == 'resolved'
    alert.source = source
    alert.severity = severity
    alert.title = title
    alert.details = details[:4000]
    if reopened:
        alert.state = 'open'
        alert.acknowledged_by = None
        alert.acknowledged_at = None
        alert.resolved_by = None
        alert.resolved_at = None
        alert.resolution_note = ''
    alert.save()
    if created or reopened:
        recipients = list(getattr(settings, 'OPERATIONS_ALERT_EMAILS', []))
        if not recipients:
            recipients = [email for _, email in getattr(settings, 'ADMINS', []) if email]
        if recipients:
            try:
                send_mail(
                    f'[{severity.upper()}] {title}',
                    f'{details}\n\nReview this alert in the Jaunpur Footwear staff operations dashboard.',
                    settings.DEFAULT_FROM_EMAIL,
                    recipients,
                    fail_silently=False,
                )
            except Exception:
                logger.exception('Could not email staff about operations alert %s.', dedupe_key)
    return alert


def _backup_state():
    configured_path = getattr(settings, 'BACKUP_HEALTHCHECK_PATH', '').strip()
    if not configured_path:
        if settings.IS_PRODUCTION:
            return 'backup-not-configured', 'critical', 'Production backup path is not configured', 'Set BACKUP_HEALTHCHECK_PATH to a directory containing completed backups.'
        return None
    path = Path(configured_path)
    if not path.exists():
        return 'backup-missing', 'critical', 'Configured backup path is missing', f'Expected backup location does not exist: {path}'
    if path.is_dir():
        try:
            backups = [item for item in path.iterdir() if item.is_file()]
        except OSError:
            backups = []
    else:
        backups = [path]
    if not backups:
        return 'backup-empty', 'critical', 'No backup files found', f'No completed backup files were found in {path}.'
    newest = max(backups, key=lambda item: item.stat().st_mtime)
    age_hours = (timezone.now().timestamp() - newest.stat().st_mtime) / 3600
    maximum_age = max(1, int(getattr(settings, 'BACKUP_MAX_AGE_HOURS', 36)))
    if age_hours > maximum_age:
        return 'backup-stale', 'critical', 'Latest backup is stale', f'The newest backup is {age_hours:.1f} hours old; the configured limit is {maximum_age} hours.'
    return None


def run_production_operations_checks():
    now = timezone.now()
    active_keys = set()
    lookback = now - timedelta(days=7)
    for run in BackgroundJobRun.objects.filter(status='failed', queued_at__gte=lookback).order_by('-queued_at'):
        key = f'failed-job-{run.pk}'
        active_keys.add(key)
        publish_alert(key, 'job', 'critical', f'Background job failed: {run.task_name}', run.error_summary or 'The background task exhausted its retries.')
    for event in PaymentWebhookEvent.objects.filter(status='failed', received_at__gte=lookback).order_by('-received_at'):
        key = f'failed-webhook-{event.pk}'
        active_keys.add(key)
        publish_alert(key, 'payment', 'critical', f'Payment webhook needs review: {event.event_type}', event.error_summary or f'Provider event {event.event_id} failed processing.')
    for refund in ReturnRefundAttempt.objects.filter(status='review_required').select_related('return_request'):
        key = f'refund-review-{refund.pk}'
        active_keys.add(key)
        publish_alert(key, 'payment', 'critical', f'Refund needs manual review for order #{refund.return_request.order_id}', refund.error_summary or 'The refund provider response needs staff review.')

    backup_state = _backup_state()
    if backup_state:
        key, severity, title, details = backup_state
        active_keys.add(key)
        publish_alert(key, 'backup', severity, title, details)

    restore_interval = max(1, int(getattr(settings, 'BACKUP_RESTORE_CHECK_INTERVAL_DAYS', 90)))
    if settings.IS_PRODUCTION:
        for check_type, label in [('database_restore', 'Database'), ('media_restore', 'Media')]:
            latest = RecoveryCheck.objects.filter(check_type=check_type).first()
            overdue = not latest or latest.status != 'passed' or latest.checked_at < now - timedelta(days=restore_interval)
            if overdue:
                key = f'restore-check-{check_type}'
                active_keys.add(key)
                if latest and latest.status == 'failed':
                    title = f'{label} restore drill failed'
                    severity = 'critical'
                    details = latest.details
                else:
                    title = f'{label} restore drill is overdue'
                    severity = 'warning'
                    details = f'Record a successful {label.lower()} restore drill. Checks are due every {restore_interval} days.'
                publish_alert(key, 'recovery', severity, title, details)
            else:
                SystemAlert.objects.filter(
                    dedupe_key=f'restore-check-{check_type}', state__in=['open', 'acknowledged'],
                ).update(state='resolved', resolved_at=now, resolution_note='A recent successful restore drill is recorded.')

    SystemAlert.objects.filter(source='backup', state__in=['open', 'acknowledged']).exclude(
        dedupe_key__in=[key for key in active_keys if key.startswith('backup-')],
    ).update(state='resolved', resolved_at=now, resolution_note='Automated backup check is healthy.')
    return len(active_keys)
