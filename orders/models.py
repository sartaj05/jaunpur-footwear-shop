from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from products.models import Product, ProductVariant
from decimal import Decimal


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=40, blank=True, default='')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self):
        unit_price = self.variant.final_price() if self.variant_id else self.product.final_price()
        return unit_price * self.quantity

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    delivery_pincode = models.CharField(max_length=10, blank=True)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_code = models.CharField(max_length=30, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, default='Cash on Delivery')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class OrderTrackingEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking_events')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'Order #{self.order_id}: {self.get_status_display()}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=200)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=40, blank=True, default='')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percent', 'Percentage'),
        ('fixed', 'Fixed amount'),
    ]

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='percent')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    starts_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    usage_limit = models.PositiveIntegerField(blank=True, null=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def is_valid_for(self, amount, at=None):
        at = at or timezone.now()
        return (
            self.is_active
            and amount >= self.minimum_order_amount
            and (self.starts_at is None or at >= self.starts_at)
            and (self.expires_at is None or at <= self.expires_at)
            and (self.usage_limit is None or self.used_count < self.usage_limit)
        )

    def discount_for(self, amount):
        if self.discount_type == 'percent':
            discount = amount * self.discount_value / Decimal('100')
        else:
            discount = self.discount_value
        return min(amount, discount).quantize(Decimal('0.01'))

    def __str__(self):
        return self.code


class DeliveryRate(models.Model):
    pincode_prefix = models.CharField(max_length=10, unique=True)
    fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    free_delivery_minimum = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.pincode_prefix} - {self.fee}'


class ReturnRequest(models.Model):
    REQUEST_TYPES = [
        ('return', 'Return'),
        ('exchange', 'Exchange'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('received', 'Item received'),
        ('completed', 'Completed'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='return_requests')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, blank=True, null=True, related_name='return_requests')
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPES)
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    staff_note = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.get_request_type_display()} for order #{self.order_id}'
