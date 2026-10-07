from django.db import transaction
from django.utils import timezone

from .models import Order, OrderTrackingEvent, PaymentAttempt
from .payments import release_order_inventory


def expire_pending_stock_reservations(*, now=None, batch_size=100, order_id=None):
    """Cancel expired, unpaid Razorpay orders and release their inventory once."""
    now = now or timezone.now()
    candidates = Order.objects.filter(
        payment_method="Razorpay",
        payment_status="pending",
        status="pending",
        stock_released=False,
        stock_reservation_expires_at__lte=now,
    )
    if order_id is not None:
        candidates = candidates.filter(pk=order_id)
    candidate_ids = list(
        candidates.order_by("stock_reservation_expires_at", "pk")
        .values_list("pk", flat=True)[:batch_size]
    )

    expired_count = 0
    for order_id in candidate_ids:
        with transaction.atomic():
            # Payment callbacks lock the attempt before the order, so keep that
            # order here to avoid deadlocks while an expiry races a webhook.
            attempts = list(
                PaymentAttempt.objects.select_for_update()
                .filter(order_id=order_id)
                .order_by("pk")
            )
            order = Order.objects.select_for_update().filter(
                pk=order_id,
                payment_method="Razorpay",
                payment_status="pending",
                status="pending",
                stock_released=False,
                stock_reservation_expires_at__lte=now,
            ).first()
            if not order or any(attempt.status == "paid" for attempt in attempts):
                continue

            for attempt in attempts:
                if attempt.status == "created":
                    attempt.status = "failed"
                    attempt.save(update_fields=["status"])

            release_order_inventory(order)
            order.status = "cancelled"
            order.payment_status = "failed"
            order.save(update_fields=["status", "payment_status"])
            OrderTrackingEvent.objects.create(
                order=order,
                status="cancelled",
                note="Online payment window expired; reserved stock was released automatically.",
            )
            expired_count += 1

    return expired_count
