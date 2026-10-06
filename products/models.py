from django.conf import settings
from django.db import models
from django.utils import timezone
from shops.models import Shop


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    GENDER_CHOICES = [
        ('men', 'Men'),
        ('women', 'Women'),
        ('kids', 'Kids'),
        ('unisex', 'Unisex'),
    ]

    name = models.CharField(max_length=200)
    name_hi = models.CharField(max_length=200, blank=True)
    seller_sku = models.CharField(max_length=64, unique=True, blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='men')
    description = models.TextField()
    description_hi = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    stock = models.PositiveIntegerField(default=0)
    available_sizes = models.CharField(
        max_length=200,
        help_text="Example: 6,7,8,9,10"
    )

    image = models.ImageField(upload_to='products/')
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.shop_id and not self.seller_sku:
            self.seller_sku = f'JFW-S{self.shop_id}-P{self.pk}'
            type(self).objects.filter(pk=self.pk).update(seller_sku=self.seller_sku)

    def final_price(self, pincode=''):
        base_price = self.discount_price if self.discount_price else self.price
        return self.price_after_promotions(base_price, pincode=pincode)

    def price_after_promotions(self, base_price, pincode=''):
        if not self.shop_id:
            return base_price
        now = timezone.now()
        promotions = self.promotions.filter(shop_id=self.shop_id, is_active=True).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gte=now),
        )
        promotional_prices = [promotion.discounted_price(base_price) for promotion in promotions if promotion.applies_to_pincode(pincode)]
        return min([base_price, *promotional_prices])

    def is_low_stock(self):
        return self.stock <= 5

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    seller_sku = models.CharField(max_length=120, unique=True, blank=True, null=True)
    size = models.CharField(max_length=10)
    color = models.CharField(max_length=40)
    stock = models.PositiveIntegerField(default=0)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['size', 'color']
        constraints = [
            models.UniqueConstraint(fields=['product', 'size', 'color'], name='unique_product_size_color')
        ]

    def final_price(self, pincode=''):
        if self.price_override is not None:
            return self.product.price_after_promotions(self.price_override, pincode=pincode)
        return self.product.final_price(pincode=pincode)

    @classmethod
    def sync_product_stock(cls, product_id):
        total = cls.objects.filter(product_id=product_id).aggregate(total=models.Sum('stock'))['total'] or 0
        Product.objects.filter(pk=product_id).update(stock=total)

    def save(self, *args, **kwargs):
        previous_product_id = None
        if self.pk:
            previous_product_id = type(self).objects.filter(pk=self.pk).values_list('product_id', flat=True).first()
        super().save(*args, **kwargs)
        if not self.seller_sku and self.product.shop_id and self.product.seller_sku:
            safe_color = ''.join(character for character in self.color.upper() if character.isalnum())[:24] or 'COLOR'
            self.seller_sku = f'{self.product.seller_sku}-{self.size}-{safe_color}-V{self.pk}'[:120]
            type(self).objects.filter(pk=self.pk).update(seller_sku=self.seller_sku)
        self.sync_product_stock(self.product_id)
        if previous_product_id and previous_product_id != self.product_id:
            self.sync_product_stock(previous_product_id)

    def delete(self, *args, **kwargs):
        product_id = self.product_id
        result = super().delete(*args, **kwargs)
        self.sync_product_stock(product_id)
        return result

    def __str__(self):
        return f'{self.product.name} - {self.size} / {self.color}'


class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    shop = models.ForeignKey(Shop, on_delete=models.SET_NULL, blank=True, null=True, related_name='products')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_user_wishlist_product')
        ]

    def __str__(self):
        return f'{self.user} saved {self.product}'


class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_reviews')
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['product', 'user'], name='unique_product_review_per_user')
        ]

    def __str__(self):
        return f'{self.rating}/5 review for {self.product}'
