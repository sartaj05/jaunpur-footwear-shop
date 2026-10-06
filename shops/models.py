from django.conf import settings
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Shop(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    VERIFICATION_CHOICES = [
        ('not_submitted', 'Not submitted'),
        ('pending', 'Verification pending'),
        ('verified', 'Verified Jaunpur shop'),
        ('needs_changes', 'More information required'),
    ]

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='footwear_shop')
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, default='Jaunpur')
    district = models.CharField(max_length=100, default='Jaunpur')
    pincode = models.CharField(max_length=6)
    description = models.TextField(blank=True)
    description_hi = models.TextField(blank=True)
    opening_hours = models.CharField(max_length=180, blank=True)
    logo = models.ImageField(upload_to='shops/logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='shops/banners/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))
    verification_status = models.CharField(max_length=16, choices=VERIFICATION_CHOICES, default='not_submitted')
    verification_requested_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='verified_jaunpur_shops')
    verification_note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(commission_rate__gte=0) & models.Q(commission_rate__lte=100),
                name='shop_commission_between_zero_and_hundred',
            ),
        ]
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'jaunpur-shop'
            candidate = base_slug
            suffix = 2
            while type(self).objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ShopReview(models.Model):
    seller_order = models.OneToOneField('orders.SellerOrder', on_delete=models.CASCADE, related_name='shop_review')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shop_reviews')
    rating = models.PositiveSmallIntegerField()
    body = models.TextField(blank=True, max_length=1200)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.CheckConstraint(condition=models.Q(rating__gte=1) & models.Q(rating__lte=5), name='shop_review_rating_1_to_5'),
        ]

    def __str__(self):
        return f'{self.rating}/5 service review for {self.shop.name}'


class ShopCoverage(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='coverage_areas')
    pincode = models.CharField(max_length=6)
    area_name = models.CharField(max_length=100, blank=True)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default='50.00')
    free_delivery_minimum = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    min_delivery_days = models.PositiveSmallIntegerField(default=1)
    max_delivery_days = models.PositiveSmallIntegerField(default=3)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['pincode']
        constraints = [
            models.UniqueConstraint(fields=['shop', 'pincode'], name='unique_shop_coverage_pincode'),
            models.CheckConstraint(condition=models.Q(max_delivery_days__gte=models.F('min_delivery_days')), name='shop_coverage_eta_range_valid'),
            models.CheckConstraint(condition=models.Q(max_delivery_days__lte=30), name='shop_coverage_eta_max_30_days'),
        ]

    def __str__(self):
        return f'{self.shop.name} - {self.area_name or self.pincode}'


class ShopFulfillmentSlot(models.Model):
    MODE_CHOICES = [('delivery', 'Local delivery'), ('pickup', 'Shop pickup')]
    WEEKDAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'),
        (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='fulfillment_slots')
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_orders = models.PositiveSmallIntegerField(default=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['weekday', 'start_time']
        constraints = [
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F('start_time')), name='shop_slot_end_after_start'),
            models.CheckConstraint(condition=models.Q(max_orders__gte=1), name='shop_slot_min_capacity_one'),
        ]

    def __str__(self):
        return f'{self.shop.name} · {self.get_weekday_display()} {self.start_time}-{self.end_time}'


class MarketplaceConnection(models.Model):
    CHANNEL_CHOICES = [('amazon', 'Amazon'), ('flipkart', 'Flipkart')]
    STATUS_CHOICES = [
        ('not_requested', 'Not requested'),
        ('pending', 'Request pending'),
        ('approved', 'Seller setup approved'),
    ]
    AUTHORIZATION_STATUS_CHOICES = [
        ('not_connected', 'Not connected'),
        ('connected', 'Seller authorized'),
        ('reauthorization_required', 'Reauthorization required'),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='marketplace_connections')
    channel = models.CharField(max_length=12, choices=CHANNEL_CHOICES)
    seller_account_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='not_requested')
    staff_note = models.TextField(blank=True)
    requested_at = models.DateTimeField(blank=True, null=True)
    authorization_status = models.CharField(max_length=24, choices=AUTHORIZATION_STATUS_CHOICES, default='not_connected')
    encrypted_access_token = models.TextField(blank=True)
    encrypted_refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    refresh_token_expires_at = models.DateTimeField(blank=True, null=True)
    authorized_at = models.DateTimeField(blank=True, null=True)
    amazon_marketplace_ids = models.CharField(max_length=700, blank=True)
    fulfillment_location_id = models.CharField(max_length=120, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['channel']
        constraints = [
            models.UniqueConstraint(fields=['shop', 'channel'], name='unique_shop_marketplace_channel')
        ]

    def __str__(self):
        return f'{self.shop.name} · {self.get_channel_display()}'


class ONDCEnrollment(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Partner request submitted'),
        ('partner_confirmed', 'Seller Network Participant confirmed'),
        ('catalog_exported', 'Catalog handoff exported'),
        ('production_approval_pending', 'Production approval pending'),
        ('live', 'Production connection confirmed'),
        ('needs_changes', 'More information required'),
    ]

    shop = models.OneToOneField(Shop, on_delete=models.CASCADE, related_name='ondc_enrollment')
    participant_name = models.CharField(max_length=160, blank=True)
    participant_contact = models.CharField(max_length=160, blank=True)
    seller_network_id = models.CharField(max_length=120, blank=True)
    participant_seller_id = models.CharField(max_length=120, blank=True)
    network_subscriber_id = models.CharField(max_length=120, blank=True)
    application_reference = models.CharField(max_length=120, blank=True)
    participant_supports_retail = models.BooleanField(default=False)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft')
    staff_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    catalog_exported_at = models.DateTimeField(blank=True, null=True)
    production_activated_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'ONDC onboarding · {self.shop.name}'


class ShopPromotion(models.Model):
    DISCOUNT_TYPES = [('percent', 'Percentage'), ('fixed', 'Fixed amount')]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='promotions')
    products = models.ManyToManyField('products.Product', related_name='promotions')
    title = models.CharField(max_length=140)
    title_hi = models.CharField(max_length=140, blank=True)
    description = models.TextField(blank=True)
    description_hi = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default='percent')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    target_pincodes = models.CharField(max_length=700, blank=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def discounted_price(self, price):
        if self.discount_type == 'percent':
            amount = price * self.discount_value / Decimal('100')
        else:
            amount = self.discount_value
        return max(Decimal('0.00'), price - min(price, amount)).quantize(Decimal('0.01'))

    def is_live(self, at=None):
        at = at or timezone.now()
        return (
            self.is_active
            and (self.starts_at is None or self.starts_at <= at)
            and (self.expires_at is None or self.expires_at >= at)
        )

    def applies_to_pincode(self, pincode=''):
        targets = {value.strip() for value in self.target_pincodes.split(',') if value.strip()}
        return not targets or bool(pincode and pincode in targets)

    def __str__(self):
        return f'{self.title} · {self.shop.name}'


class MarketplaceProductMapping(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft mapping'),
        ('submitted', 'Submitted to marketplace'),
        ('active', 'Active listing'),
        ('needs_attention', 'Needs attention'),
    ]

    connection = models.ForeignKey(MarketplaceConnection, on_delete=models.CASCADE, related_name='product_mappings')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, related_name='marketplace_mappings')
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.PROTECT, blank=True, null=True, related_name='marketplace_mappings')
    external_sku = models.CharField(max_length=120)
    external_listing_id = models.CharField(max_length=160, blank=True)
    category_path = models.CharField(max_length=240, blank=True)
    allocated_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    error_text = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['connection__channel', 'external_sku']
        constraints = [
            models.UniqueConstraint(fields=['connection', 'external_sku'], name='unique_channel_external_sku'),
            models.UniqueConstraint(fields=['connection', 'product'], condition=models.Q(variant__isnull=True), name='unique_channel_product_base_mapping'),
            models.UniqueConstraint(fields=['connection', 'product', 'variant'], condition=models.Q(variant__isnull=False), name='unique_channel_product_variant_mapping'),
        ]

    def __str__(self):
        return f'{self.connection.get_channel_display()} · {self.external_sku}'


class MarketplaceSyncRun(models.Model):
    STATUS_CHOICES = [('running', 'Running'), ('succeeded', 'Succeeded'), ('failed', 'Failed')]

    connection = models.ForeignKey(MarketplaceConnection, on_delete=models.CASCADE, related_name='sync_runs')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='running')
    orders_seen = models.PositiveIntegerField(default=0)
    order_items_seen = models.PositiveIntegerField(default=0)
    inventory_updates = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.connection.get_channel_display()} sync · {self.get_status_display()}'


class MarketplaceChannelOrder(models.Model):
    RECONCILIATION_CHOICES = [('open', 'Needs reconciliation'), ('reconciled', 'Reconciled')]

    connection = models.ForeignKey(MarketplaceConnection, on_delete=models.CASCADE, related_name='channel_orders')
    external_order_id = models.CharField(max_length=160)
    marketplace_id = models.CharField(max_length=40, blank=True)
    external_status = models.CharField(max_length=80, blank=True)
    purchased_at = models.DateTimeField(blank=True, null=True)
    currency = models.CharField(max_length=3, default='INR')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    marketplace_fee = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    settlement_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    settlement_reference = models.CharField(max_length=160, blank=True)
    reconciliation_status = models.CharField(max_length=12, choices=RECONCILIATION_CHOICES, default='open')
    reconciled_at = models.DateTimeField(blank=True, null=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-purchased_at', '-created_at']
        constraints = [models.UniqueConstraint(fields=['connection', 'external_order_id'], name='unique_marketplace_channel_order')]

    def __str__(self):
        return f'{self.connection.get_channel_display()} order {self.external_order_id}'


class MarketplaceSettlementImport(models.Model):
    connection = models.ForeignKey(MarketplaceConnection, on_delete=models.PROTECT, related_name='settlement_imports')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='marketplace_settlement_imports')
    source_filename = models.CharField(max_length=180)
    rows_seen = models.PositiveIntegerField(default=0)
    rows_updated = models.PositiveIntegerField(default=0)
    rows_failed = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.connection.get_channel_display()} settlement import · {self.created_at:%Y-%m-%d}'


class MarketplaceSettlementLine(models.Model):
    STATUS_CHOICES = [('matched', 'Order matched'), ('missing_order', 'Order not found'), ('invalid', 'Invalid row')]
    settlement_import = models.ForeignKey(MarketplaceSettlementImport, on_delete=models.CASCADE, related_name='lines')
    order = models.ForeignKey(MarketplaceChannelOrder, on_delete=models.SET_NULL, blank=True, null=True, related_name='settlement_lines')
    external_order_id = models.CharField(max_length=160, blank=True)
    marketplace_fee = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    settlement_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    settlement_reference = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    error_summary = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.external_order_id or "Unknown order"} · {self.get_status_display()}'


class MarketplaceChannelOrderItem(models.Model):
    INVENTORY_CHOICES = [
        ('pending', 'Pending inventory reservation'),
        ('reserved', 'Reserved from shared stock'),
        ('shortage', 'Stock shortage'),
        ('unmapped', 'SKU needs mapping'),
        ('released', 'Reservation released'),
        ('sold', 'Fulfilled from reserved stock'),
    ]

    order = models.ForeignKey(MarketplaceChannelOrder, on_delete=models.CASCADE, related_name='items')
    external_item_id = models.CharField(max_length=160)
    external_sku = models.CharField(max_length=120, blank=True)
    mapping = models.ForeignKey(MarketplaceProductMapping, on_delete=models.SET_NULL, blank=True, null=True, related_name='channel_order_items')
    quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='INR')
    external_status = models.CharField(max_length=80, blank=True)
    inventory_status = models.CharField(max_length=12, choices=INVENTORY_CHOICES, default='pending')
    consumed_quantity = models.PositiveIntegerField(default=0)
    allocation_consumed_quantity = models.PositiveIntegerField(default=0)
    allocation_processed_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['order', 'external_item_id'], name='unique_marketplace_channel_order_item')]

    def __str__(self):
        return f'{self.order.external_order_id} · {self.external_sku or self.external_item_id}'
