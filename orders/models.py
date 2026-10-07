from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from products.models import Product, ProductVariant
from shops.models import Shop, ShopFulfillmentSlot
from decimal import Decimal


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=40, blank=True, default='')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)

    def total_price(self, pincode=''):
        unit_price = self.variant.final_price(pincode=pincode) if self.variant_id else self.product.final_price(pincode=pincode)
        return unit_price * self.quantity

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('pending', 'Payment pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
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
    payment_status = models.CharField(max_length=12, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    stock_released = models.BooleanField(default=False)
    stock_reservation_expires_at = models.DateTimeField(blank=True, null=True, db_index=True)

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


class SellerOrder(models.Model):
    PAYOUT_STATUS_CHOICES = [('pending', 'Pending payout'), ('paid', 'Paid out')]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for delivery'),
        ('delivered', 'Delivered'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='seller_orders')
    shop = models.ForeignKey(Shop, on_delete=models.SET_NULL, blank=True, null=True, related_name='seller_orders')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sales_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payout_status = models.CharField(max_length=10, choices=PAYOUT_STATUS_CHOICES, default='pending')
    payout_reference = models.CharField(max_length=120, blank=True)
    paid_out_at = models.DateTimeField(blank=True, null=True)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    fulfillment_method = models.CharField(max_length=10, choices=[('delivery', 'Local delivery'), ('pickup', 'Shop pickup')], default='delivery')
    fulfillment_date = models.DateField(blank=True, null=True)
    fulfillment_slot = models.ForeignKey(ShopFulfillmentSlot, on_delete=models.SET_NULL, blank=True, null=True, related_name='seller_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        seller = self.shop.name if self.shop_id else 'Jaunpur Footwear'
        return f'{seller} · order #{self.order_id}'


class DeliveryRider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_rider_profile')
    phone = models.CharField(max_length=15, blank=True)
    home_pincode = models.CharField(max_length=6, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class DeliveryRun(models.Model):
    STATUS_CHOICES = [('planned', 'Planned'), ('in_progress', 'In progress'), ('completed', 'Completed')]

    rider = models.ForeignKey(DeliveryRider, on_delete=models.PROTECT, related_name='runs')
    pincode = models.CharField(max_length=6)
    delivery_date = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='planned')
    route_note = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='created_delivery_runs')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['delivery_date', 'pincode', 'id']

    def __str__(self):
        return f'{self.pincode} · {self.delivery_date} · {self.rider}'


class DeliveryAssignment(models.Model):
    STATUS_CHOICES = [('assigned', 'Assigned'), ('delivered', 'Delivered'), ('failed', 'Delivery attempt failed')]

    run = models.ForeignKey(DeliveryRun, on_delete=models.CASCADE, related_name='assignments')
    seller_order = models.OneToOneField(SellerOrder, on_delete=models.CASCADE, related_name='delivery_assignment')
    sequence = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='assigned')
    delivered_to = models.CharField(max_length=120, blank=True)
    proof_photo = models.ImageField(upload_to='delivery/proof/', blank=True, null=True)
    note = models.TextField(blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['run', 'sequence']
        constraints = [models.UniqueConstraint(fields=['run', 'sequence'], name='unique_delivery_run_stop_sequence')]

    def __str__(self):
        return f'Stop {self.sequence} · {self.seller_order}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    seller_order = models.ForeignKey(SellerOrder, on_delete=models.SET_NULL, blank=True, null=True, related_name='items')
    product_name = models.CharField(max_length=200)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=40, blank=True, default='')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True, related_name='order_items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, blank=True, null=True, related_name='order_items')
    used_variant = models.BooleanField(default=False)


class PaymentAttempt(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_attempts')
    provider = models.CharField(max_length=20, default='razorpay')
    gateway_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    gateway_payment_id = models.CharField(max_length=100, blank=True)
    amount_subunits = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']


class PaymentWebhookEvent(models.Model):
    event_id = models.CharField(max_length=160, unique=True)
    event_type = models.CharField(max_length=100)
    status = models.CharField(max_length=12, choices=[('received', 'Received'), ('processed', 'Processed'), ('failed', 'Failed')], default='received')
    error_summary = models.CharField(max_length=240, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return f'{self.event_type} · {self.event_id}'


class ReturnRefundAttempt(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('submitted', 'Refund submitted to provider'),
        ('review_required', 'Manual review required'),
    ]
    return_request = models.OneToOneField(ReturnRequest, on_delete=models.PROTECT, related_name='refund_attempt')
    amount_subunits = models.PositiveBigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    provider_refund_id = models.CharField(max_length=120, blank=True)
    error_summary = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Return #{self.return_request_id} refund · {self.get_status_display()}'


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
    reserved_for = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='reserved_coupons')

    def is_valid_for(self, amount, at=None, user=None):
        at = at or timezone.now()
        return (
            self.is_active
            and (self.reserved_for_id is None or (user is not None and self.reserved_for_id == user.pk))
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
    REFUND_STATUS_CHOICES = [
        ('not_applicable', 'Not applicable'),
        ('pending', 'Refund pending'),
        ('processed', 'Refund recorded as sent'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='return_requests')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='return_requests')
    order_item = models.ForeignKey(OrderItem, on_delete=models.SET_NULL, blank=True, null=True, related_name='return_requests')
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPES)
    exchange_size = models.CharField(max_length=10, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    pickup_required = models.BooleanField(default=True)
    pickup_scheduled_at = models.DateTimeField(blank=True, null=True)
    refund_status = models.CharField(max_length=16, choices=REFUND_STATUS_CHOICES, default='not_applicable')
    refund_reference = models.CharField(max_length=120, blank=True)
    staff_note = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.get_request_type_display()} for order #{self.order_id}'
