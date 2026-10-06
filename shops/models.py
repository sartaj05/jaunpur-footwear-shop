from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Shop(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
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
    opening_hours = models.CharField(max_length=180, blank=True)
    logo = models.ImageField(upload_to='shops/logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='shops/banners/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
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
