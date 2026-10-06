from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.models import Order
from products.models import Brand, Category, Product


class MarketplaceApiTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Local Brand")
        self.category = Category.objects.create(name="Footwear")
        self.product = Product.objects.create(
            name="Jaunpur Runner", brand=self.brand, category=self.category,
            description="Everyday shoe", price=Decimal("899.00"), stock=4,
            available_sizes="7,8", image="products/runner.jpg",
        )

    def test_products_are_public_and_searchable(self):
        response = self.client.get(reverse("api-products"), {"q": "Runner"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.product.pk)

    def test_my_orders_requires_login_and_returns_only_the_current_users_orders(self):
        buyer = User.objects.create_user(username="buyer", password="buyer-password")
        other = User.objects.create_user(username="other", password="other-password")
        own_order = Order.objects.create(
            user=buyer, full_name="Buyer", mobile="9000000001", address="Jaunpur",
            total_amount=Decimal("899.00"),
        )
        Order.objects.create(
            user=other, full_name="Other", mobile="9000000002", address="Jaunpur",
            total_amount=Decimal("1200.00"),
        )

        url = reverse("api-my-orders")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(buyer)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()["results"]], [own_order.pk])
