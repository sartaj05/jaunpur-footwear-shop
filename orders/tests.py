from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from datetime import time, timedelta
from django.utils import timezone

from products.models import Brand, Category, Product
from products.models import InventoryMovement
from shops.models import Shop, ShopCoverage, ShopFulfillmentSlot
from .views import checkout_seller_groups

from .models import CartItem, Order, OrderItem


class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyer", password="test-password-123")
        self.brand = Brand.objects.create(name="Jaunpur Brand")
        self.category = Category.objects.create(name="Shoes")
        self.product = Product.objects.create(
            name="Everyday Shoe",
            brand=self.brand,
            category=self.category,
            description="Comfortable everyday footwear.",
            price=Decimal("1200.00"),
            stock=3,
            available_sizes="7,8,9",
            image="products/test-shoe.jpg",
        )
        self.client.force_login(self.user)

    @patch("orders.tasks.send_order_confirmation")
    def test_cash_on_delivery_creates_order_and_decrements_stock(self, send_confirmation):
        CartItem.objects.create(user=self.user, product=self.product, size="8", quantity=2)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("checkout"), {
                "payment_method": "cod",
                "pincode": "222001",
                "full_name": "Test Buyer",
                "mobile": "9876543210",
                "address": "Test address, Jaunpur",
                "fulfillment_platform": "delivery",
            })

        self.assertRedirects(response, reverse("my_orders"))
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.payment_status, "unpaid")
        self.assertEqual(order.total_amount, Decimal("1250.00"))
        self.assertEqual(OrderItem.objects.get(order=order).quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        movement = InventoryMovement.objects.get(reason="order_sale")
        self.assertEqual(movement.delta, -2)
        self.assertEqual(movement.stock_after, 1)
        self.assertEqual(movement.reference, f"order-item:{OrderItem.objects.get(order=order).pk}")
        self.assertEqual(movement.actor, self.user)
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())
        send_confirmation.assert_called_once_with(order.pk)

    def test_checkout_rejects_quantity_above_stock_without_creating_order(self):
        CartItem.objects.create(user=self.user, product=self.product, size="8", quantity=4)

        response = self.client.post(reverse("checkout"), {
            "payment_method": "cod",
            "pincode": "222001",
            "full_name": "Test Buyer",
            "mobile": "9876543210",
            "address": "Test address, Jaunpur",
        })

        self.assertRedirects(response, reverse("cart"))
        self.assertFalse(Order.objects.filter(user=self.user).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(CartItem.objects.get(user=self.user).quantity, 4)

    def test_customer_cannot_remove_another_customers_cart_item(self):
        other_user = User.objects.create_user(username="other", password="test-password-456")
        item = CartItem.objects.create(user=other_user, product=self.product, size="8", quantity=1)

        response = self.client.post(reverse("remove_cart_item", args=[item.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=item.pk).exists())

    def test_seller_delivery_eta_is_shown_for_covered_pin(self):
        shop = Shop.objects.create(
            owner=self.user, name="Jaunpur Runner Shop", phone="9000000000",
            address="Jaunpur", pincode="222001", status="approved",
        )
        ShopCoverage.objects.create(
            shop=shop, pincode="222001", min_delivery_days=2, max_delivery_days=4,
        )
        ShopFulfillmentSlot.objects.create(
            shop=shop, mode="delivery", weekday=0,
            start_time=time(10, 0), end_time=time(12, 0), max_orders=3,
        )
        self.product.shop = shop
        self.product.save(update_fields=["shop"])
        cart_item = CartItem.objects.create(user=self.user, product=self.product, size="8", quantity=1)

        seller = checkout_seller_groups([cart_item], "222001")[0]

        self.assertTrue(seller["delivery_available"])
        self.assertEqual(seller["delivery_eta_start"], (timezone.localdate() + timedelta(days=2)).isoformat())
        self.assertEqual(seller["delivery_eta_end"], (timezone.localdate() + timedelta(days=4)).isoformat())
