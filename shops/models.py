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


class ShopCoverage(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='coverage_areas')
    pincode = models.CharField(max_length=6)
    area_name = models.CharField(max_length=100, blank=True)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default='50.00')
    free_delivery_minimum = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['pincode']
        constraints = [
            models.UniqueConstraint(fields=['shop', 'pincode'], name='unique_shop_coverage_pincode')
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

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='marketplace_connections')
    channel = models.CharField(max_length=12, choices=CHANNEL_CHOICES)
    seller_account_id = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='not_requested')
    staff_note = models.TextField(blank=True)
    requested_at = models.DateTimeField(blank=True, null=True)
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
        ('onboarded', 'Seller onboarding recorded'),
        ('rejected', 'More information required'),
    ]

    shop = models.OneToOneField(Shop, on_delete=models.CASCADE, related_name='ondc_enrollment')
    participant_name = models.CharField(max_length=160, blank=True)
    participant_contact = models.CharField(max_length=160, blank=True)
    seller_network_id = models.CharField(max_length=120, blank=True)
    application_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    staff_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
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
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='marketplace_mappings')
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.CASCADE, blank=True, null=True, related_name='marketplace_mappings')
    external_sku = models.CharField(max_length=120)
    external_listing_id = models.CharField(max_length=160, blank=True)
    category_path = models.CharField(max_length=240, blank=True)
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
