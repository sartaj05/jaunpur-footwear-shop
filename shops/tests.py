from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.models import Order, SellerOrder
from .models import Shop, ShopReview


class VerifiedShopReviewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="shop-owner", password="owner-password")
        self.customer = User.objects.create_user(username="shop-customer", password="customer-password")
        self.shop = Shop.objects.create(
            owner=self.owner, name="Jaunpur Shoes", phone="9000000000",
            address="Jaunpur market", pincode="222001", status="approved",
        )
        self.order = Order.objects.create(
            user=self.customer, full_name="Customer", mobile="9000000001",
            address="Jaunpur", total_amount=Decimal("500.00"),
        )
        self.seller_order = SellerOrder.objects.create(
            order=self.order, shop=self.shop, status="delivered",
            subtotal=Decimal("500.00"), sales_amount=Decimal("500.00"),
        )

    def test_only_delivered_order_customer_can_review_shop(self):
        self.client.force_login(self.customer)
        url = reverse("review_shop", args=[self.seller_order.pk])

        response = self.client.post(url, {"rating": "5", "body": "Fast local delivery."})

        self.assertEqual(response.status_code, 302)
        review = ShopReview.objects.get(seller_order=self.seller_order)
        self.assertEqual(review.shop, self.shop)
        self.assertEqual(review.customer, self.customer)
        self.assertEqual(review.rating, 5)

    def test_review_is_denied_before_delivery(self):
        self.seller_order.status = "packed"
        self.seller_order.save(update_fields=["status"])
        self.client.force_login(self.customer)

        response = self.client.get(reverse("review_shop", args=[self.seller_order.pk]))

        self.assertEqual(response.status_code, 404)
