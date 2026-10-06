import hashlib
import hmac
import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Order, OrderTrackingEvent, PaymentAttempt, PaymentWebhookEvent


@override_settings(RAZORPAY_WEBHOOK_SECRET="webhook-test-secret")
class RazorpayWebhookTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="webhook-buyer", password="test-password")
        self.order = Order.objects.create(
            user=user,
            full_name="Webhook Buyer",
            mobile="9000000000",
            address="Jaunpur",
            total_amount=Decimal("899.00"),
            payment_method="Razorpay",
            payment_status="pending",
        )
        self.attempt = PaymentAttempt.objects.create(
            order=self.order,
            gateway_order_id="order_test_123",
            amount_subunits=89900,
            currency="INR",
        )
        self.payload = json.dumps({
            "event": "payment.captured",
            "payload": {"payment": {"entity": {
                "id": "pay_test_456",
                "order_id": "order_test_123",
                "amount": 89900,
                "currency": "INR",
                "status": "captured",
            }}},
        }).encode()

    def _send(self, event_id="evt_test_1", body=None):
        body = body or self.payload
        signature = hmac.new(b"webhook-test-secret", body, hashlib.sha256).hexdigest()
        return self.client.post(
            reverse("razorpay_webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID=event_id,
        )

    def test_captured_payment_confirms_order_and_duplicate_delivery_is_idempotent(self):
        self.assertEqual(self._send().status_code, 200)
        self.assertEqual(self._send().status_code, 200)

        self.attempt.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.attempt.status, "paid")
        self.assertEqual(self.attempt.gateway_payment_id, "pay_test_456")
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(self.order.status, "confirmed")
        self.assertEqual(OrderTrackingEvent.objects.filter(order=self.order).count(), 1)
        self.assertEqual(PaymentWebhookEvent.objects.filter(status="processed").count(), 1)

    def test_invalid_webhook_signature_is_rejected(self):
        response = self.client.post(
            reverse("razorpay_webhook"),
            data=self.payload,
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="invalid",
            HTTP_X_RAZORPAY_EVENT_ID="evt_bad",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PaymentWebhookEvent.objects.exists())
