from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from products.models import Brand, Category, InventoryMovement, Product

from .models import Order, OrderItem, PaymentAttempt, ReturnRefundAttempt, ReturnRequest
from .refunds import process_return_refund


class ReturnRefundTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="refund-buyer", password="test-password")
        brand = Brand.objects.create(name="Refund Brand")
        category = Category.objects.create(name="Refund Shoes")
        self.product = Product.objects.create(
            name="Returned Shoe", brand=brand, category=category,
            description="Shoe for return", price=Decimal("900.00"), stock=1,
            available_sizes="8", image="products/return-shoe.jpg",
        )
        order = Order.objects.create(
            user=user, full_name="Refund Buyer", mobile="9000000000", address="Jaunpur",
            total_amount=Decimal("900.00"), payment_method="Razorpay", payment_status="paid",
        )
        item = OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            size="8", quantity=1, price=Decimal("900.00"),
        )
        self.return_request = ReturnRequest.objects.create(
            customer=user, order=order, order_item=item, request_type="return",
            reason="Wrong size", status="received", refund_status="pending",
        )
        PaymentAttempt.objects.create(
            order=order, gateway_order_id="pay_order_1", gateway_payment_id="pay_1",
            amount_subunits=90000, status="paid",
        )

    @patch("orders.refunds.create_razorpay_refund")
    def test_received_return_refund_is_recorded_once_and_restocks_item(self, create_refund):
        create_refund.return_value = {"id": "rfnd_1", "payment_id": "pay_1", "amount": 90000}

        result = process_return_refund(self.return_request.pk)
        duplicate_result = process_return_refund(self.return_request.pk)

        self.return_request.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(result.status, "submitted")
        self.assertIsNone(duplicate_result)
        self.assertEqual(create_refund.call_count, 1)
        self.assertEqual(self.return_request.refund_status, "processed")
        self.assertEqual(self.return_request.status, "completed")
        self.assertEqual(self.product.stock, 2)
        movement = InventoryMovement.objects.get(reason="customer_return")
        self.assertEqual(movement.delta, 1)

    @patch("orders.refunds.create_razorpay_refund")
    def test_mismatched_provider_response_requires_manual_review(self, create_refund):
        create_refund.return_value = {"id": "rfnd_wrong", "payment_id": "pay_other", "amount": 90000}

        result = process_return_refund(self.return_request.pk)

        self.return_request.refresh_from_db()
        self.assertEqual(result.status, "review_required")
        self.assertEqual(self.return_request.refund_status, "pending")
        self.assertEqual(self.product.stock, 1)
