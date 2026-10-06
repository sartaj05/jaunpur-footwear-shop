import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import ReferralReward

from .models import Coupon, Order, OrderTrackingEvent, PaymentAttempt, PaymentWebhookEvent
from .notifications import send_order_confirmation

logger = logging.getLogger(__name__)


def _signature_is_valid(body, signature, secret):
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not secret:
        return JsonResponse({"error": "webhook_not_configured"}, status=503)
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not _signature_is_valid(request.body, signature, secret):
        return JsonResponse({"error": "invalid_signature"}, status=400)
    event_id = request.headers.get("X-Razorpay-Event-Id", "").strip()
    if not event_id:
        return JsonResponse({"error": "missing_event_id"}, status=400)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid_json"}, status=400)

    event_type = str(payload.get("event", "unknown"))[:100]
    with transaction.atomic():
        event, _created = PaymentWebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={"event_type": event_type},
        )
        event = PaymentWebhookEvent.objects.select_for_update().get(pk=event.pk)
        if event.status == "processed":
            return JsonResponse({"status": "duplicate_ignored"})

        if event_type == "payment.captured":
            entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            attempt = PaymentAttempt.objects.select_for_update().filter(
                gateway_order_id=entity.get("order_id", "")
            ).select_related("order").first()
            if not attempt:
                event.status = "failed"
                event.error_summary = "No payment attempt matches the gateway order."
                event.save(update_fields=["status", "error_summary"])
                logger.warning("Razorpay capture has no matching attempt; event=%s", event_id)
                return JsonResponse({"status": "recorded_for_review"})

            order = Order.objects.select_for_update().get(pk=attempt.order_id)
            try:
                captured_amount = int(entity.get("amount", -1))
            except (TypeError, ValueError):
                captured_amount = -1
            valid_capture = (
                entity.get("status") == "captured"
                and entity.get("id")
                and captured_amount == attempt.amount_subunits
                and entity.get("currency") == attempt.currency
            )
            if not valid_capture:
                event.status = "failed"
                event.error_summary = "Capture amount, currency, or status did not match the payment attempt."
                event.save(update_fields=["status", "error_summary"])
                logger.error("Razorpay capture did not match its attempt; event=%s attempt=%s", event_id, attempt.pk)
                return JsonResponse({"status": "recorded_for_review"})

            if attempt.status == "created" and order.stock_released:
                event.status = "failed"
                event.error_summary = "Payment arrived after the order stock reservation was released."
                event.save(update_fields=["status", "error_summary"])
                logger.critical("Captured Razorpay payment has no active stock reservation; order=%s event=%s", order.pk, event_id)
                return JsonResponse({"status": "recorded_for_review"})
            if attempt.status == "created":
                attempt.status = "paid"
                attempt.gateway_payment_id = str(entity["id"])
                attempt.paid_at = timezone.now()
                attempt.save(update_fields=["status", "gateway_payment_id", "paid_at"])
                order.payment_status = "paid"
                order.status = "confirmed"
                order.save(update_fields=["payment_status", "status"])
                OrderTrackingEvent.objects.create(
                    order=order,
                    status="confirmed",
                    note="Payment capture confirmed by payment provider webhook",
                )
                if order.coupon_code:
                    Coupon.objects.filter(code=order.coupon_code).update(used_count=F("used_count") + 1)
                    ReferralReward.objects.filter(
                        reward_coupon_code=order.coupon_code,
                        status="earned",
                    ).update(status="redeemed")
                transaction.on_commit(lambda order_id=order.pk: send_order_confirmation(order_id))
            elif attempt.status == "paid" and attempt.gateway_payment_id != str(entity["id"]):
                event.status = "failed"
                event.error_summary = "A different payment is already recorded for this attempt."
                event.save(update_fields=["status", "error_summary"])
                logger.error("Conflicting Razorpay payment for attempt=%s event=%s", attempt.pk, event_id)
                return JsonResponse({"status": "recorded_for_review"})

        event.status = "processed"
        event.processed_at = timezone.now()
        event.error_summary = ""
        event.save(update_fields=["status", "processed_at", "error_summary"])
    return JsonResponse({"status": "processed"})
