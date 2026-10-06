from celery import shared_task
from django.utils import timezone

from dashboard.models import BackgroundJobRun
from .notifications import send_order_confirmation, send_order_status_update


class NotificationDeliveryError(Exception):
    pass


def _run_notification(task, delivery_function, order_id, job_id):
    run = BackgroundJobRun.objects.filter(pk=job_id).first() if job_id else None
    if run:
        run.status = "running"
        run.started_at = timezone.now()
        run.retry_count = task.request.retries
        run.error_summary = ""
        run.save(update_fields=["status", "started_at", "retry_count", "error_summary"])
    try:
        if not delivery_function(order_id):
            raise NotificationDeliveryError("One or more configured notification channels did not accept the message.")
    except Exception as exc:
        if run:
            run.status = "failed" if task.request.retries >= 5 else "pending"
            run.error_summary = f"{exc.__class__.__name__}: notification failed"[:300]
            if run.status == "failed":
                run.finished_at = timezone.now()
            run.save(update_fields=["status", "error_summary", "finished_at"])
        if isinstance(exc, NotificationDeliveryError):
            raise
        raise NotificationDeliveryError("Notification provider request failed.") from exc
    if run:
        run.status = "succeeded"
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "finished_at"])


@shared_task(bind=True, autoretry_for=(NotificationDeliveryError,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 5})
def send_order_confirmation_task(self, order_id, job_id=None):
    _run_notification(self, send_order_confirmation, order_id, job_id)


@shared_task(bind=True, autoretry_for=(NotificationDeliveryError,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 5})
def send_order_status_update_task(self, order_id, job_id=None):
    _run_notification(self, send_order_status_update, order_id, job_id)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 5})
def sync_marketplace_channels_task(self, shop_id=None, channel=None, job_id=None):
    from shops.marketplace_sync import sync_marketplace_connection
    from shops.models import MarketplaceConnection

    run_record = BackgroundJobRun.objects.filter(pk=job_id).first() if job_id else None
    if run_record:
        run_record.status = "running"
        run_record.started_at = timezone.now()
        run_record.retry_count = self.request.retries
        run_record.error_summary = ""
        run_record.save(update_fields=["status", "started_at", "retry_count", "error_summary"])
    try:
        connections = MarketplaceConnection.objects.filter(
            status="approved", authorization_status="connected",
        ).select_related("shop")
        if shop_id:
            connections = connections.filter(shop_id=shop_id)
        if channel:
            connections = connections.filter(channel=channel)
        failed = []
        for connection in connections.order_by("shop_id", "channel"):
            sync_run = sync_marketplace_connection(connection)
            if sync_run.status != "succeeded":
                failed.append(sync_run.error_summary or f"{connection.shop_id}/{connection.channel} failed")
        if failed:
            raise RuntimeError("; ".join(failed)[:300])
    except Exception as exc:
        if run_record:
            run_record.status = "failed" if self.request.retries >= 5 else "pending"
            run_record.error_summary = str(exc)[:300]
            if run_record.status == "failed":
                run_record.finished_at = timezone.now()
            run_record.save(update_fields=["status", "error_summary", "finished_at"])
        raise
    if run_record:
        run_record.status = "succeeded"
        run_record.finished_at = timezone.now()
        run_record.save(update_fields=["status", "finished_at"])
