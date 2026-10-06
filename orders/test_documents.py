from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Order


class OrderInvoiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="invoice-buyer", password="test-password")
        self.order = Order.objects.create(
            user=self.user, full_name="Invoice Buyer", mobile="9000000000",
            address="Jaunpur", delivery_pincode="222001", total_amount=Decimal("50.00"),
        )

    def test_customer_can_download_own_pdf_receipt(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("order_invoice", args=[self.order.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_customer_cannot_download_another_customers_receipt(self):
        other = User.objects.create_user(username="other-invoice-buyer", password="test-password")
        self.client.force_login(other)

        response = self.client.get(reverse("order_invoice", args=[self.order.pk]))

        self.assertEqual(response.status_code, 404)
