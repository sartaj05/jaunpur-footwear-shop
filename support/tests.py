from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.models import Order

from .models import SupportMessage, SupportTicket


class CustomerSupportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="support-buyer", password="test-password")
        self.other = User.objects.create_user(username="other-buyer", password="test-password")
        self.order = Order.objects.create(
            user=self.user, full_name="Support Buyer", mobile="9000000000",
            address="Jaunpur", total_amount=Decimal("500.00"),
        )
        self.ticket = SupportTicket.objects.create(
            user=self.user, order=self.order, subject="Where is my order?",
            category="delivery", description="Please share an update on this delivery.",
        )

    def test_customer_can_create_ticket_for_own_order(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("support_create"), {
            "subject": "Payment question",
            "category": "payment",
            "description": "I need help understanding my payment status.",
            "order_id": str(self.order.pk),
        })

        self.assertEqual(response.status_code, 302)
        ticket = SupportTicket.objects.get(subject="Payment question")
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.order, self.order)

    def test_customer_cannot_attach_another_customers_order(self):
        other_order = Order.objects.create(
            user=self.other, full_name="Other", mobile="9000000001", address="Jaunpur",
            total_amount=Decimal("700.00"),
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse("support_create"), {
            "subject": "Order issue",
            "category": "order",
            "description": "Please help with this order.",
            "order_id": str(other_order.pk),
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SupportTicket.objects.filter(subject="Order issue").exists())

    def test_ticket_is_private_and_customer_can_reply(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("support_detail", args=[self.ticket.pk])).status_code, 404)

        self.client.force_login(self.user)
        response = self.client.post(reverse("support_detail", args=[self.ticket.pk]), {"message": "Thank you for checking."})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(SupportMessage.objects.get(ticket=self.ticket).author, self.user)
