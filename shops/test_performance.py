from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from orders.models import Order, SellerOrder
from support.models import SupportTicket

from .models import Shop, ShopReview
from .performance import performance_for_shops


class SellerServicePerformanceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='performance-owner', password='test-password')
        self.customer = User.objects.create_user(username='performance-buyer', password='test-password')
        self.shop = Shop.objects.create(
            owner=self.owner,
            name='Performance Shoes',
            phone='9000000000',
            address='Jaunpur market',
            pincode='222001',
            status='approved',
        )

    def test_service_metrics_use_delivered_samples_and_shop_linked_issues(self):
        delivered_order = Order.objects.create(
            user=self.customer,
            full_name='Buyer',
            mobile='9000000001',
            address='Jaunpur',
            total_amount=Decimal('800.00'),
        )
        delivered_seller_order = SellerOrder.objects.create(
            order=delivered_order,
            shop=self.shop,
            status='delivered',
            delivered_at=timezone.now(),
            fulfillment_date=timezone.localdate(),
        )
        cancelled_order = Order.objects.create(
            user=self.customer,
            full_name='Buyer',
            mobile='9000000001',
            address='Jaunpur',
            total_amount=Decimal('600.00'),
            status='cancelled',
        )
        SellerOrder.objects.create(order=cancelled_order, shop=self.shop)
        ShopReview.objects.create(
            seller_order=delivered_seller_order,
            shop=self.shop,
            customer=self.customer,
            rating=5,
            body='Delivered as scheduled.',
        )
        SupportTicket.objects.create(
            user=self.customer,
            order=delivered_order,
            shop=self.shop,
            subject='Delivery concern',
            category='delivery',
            description='Please check this delivery status.',
        )

        metrics = performance_for_shops([self.shop], since=timezone.now() - timedelta(days=30))[self.shop.pk]

        self.assertEqual(metrics['order_count'], 2)
        self.assertEqual(metrics['delivered_count'], 1)
        self.assertEqual(metrics['cancellation_rate'], 50.0)
        self.assertEqual(metrics['on_time_sample_count'], 1)
        self.assertEqual(metrics['on_time_rate'], 100.0)
        self.assertEqual(metrics['review_count'], 1)
        self.assertEqual(float(metrics['average_rating']), 5.0)
        self.assertEqual(metrics['complaint_count'], 1)
        self.assertEqual(metrics['open_complaint_count'], 1)

    def test_public_storefront_displays_sample_aware_metrics(self):
        response = self.client.get(reverse('shop_page', kwargs={'slug': self.shop.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertIn('service_metrics', response.context)
        self.assertContains(response, 'Recent service')
