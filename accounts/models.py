import secrets

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Jaunpur')
    pincode = models.CharField(max_length=10, blank=True)
    preferred_language = models.CharField(max_length=2, choices=[('en', 'English'), ('hi', 'Hindi')], default='en')
    email_order_updates = models.BooleanField(default=True)
    whatsapp_order_updates = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class CustomerAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_addresses')
    label = models.CharField(max_length=40, default='Home')
    recipient_name = models.CharField(max_length=150)
    mobile = models.CharField(max_length=18)
    address = models.TextField(max_length=1000)
    city = models.CharField(max_length=100, default='Jaunpur')
    pincode = models.CharField(max_length=6)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'label', 'id']

    def __str__(self):
        return f'{self.label} · {self.recipient_name} · {self.pincode}'


class ReferralCode(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_code')
    code = models.CharField(max_length=16, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f'JP{secrets.token_hex(4).upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class ReferralReward(models.Model):
    STATUS_CHOICES = [('pending', 'Waiting for first order'), ('earned', 'Earned'), ('redeemed', 'Coupon used')]
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_rewards')
    referred_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_attribution')
    amount = models.DecimalField(max_digits=8, decimal_places=2, default='100.00')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reward_coupon_code = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    earned_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f'{self.referrer} referred {self.referred_user} · {self.get_status_display()}'


class LoyaltyAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loyalty_account')
    points = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} · {self.points} Jaunpur points'


class LoyaltyTransaction(models.Model):
    TYPE_CHOICES = [('earned', 'Points earned'), ('redeemed', 'Points redeemed')]

    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, blank=True, null=True, related_name='loyalty_transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    points = models.PositiveIntegerField()
    coupon_code = models.CharField(max_length=30, blank=True)
    note = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['order', 'transaction_type'], condition=models.Q(order__isnull=False), name='unique_order_loyalty_transaction'),
        ]

    def __str__(self):
        return f'{self.get_transaction_type_display()} · {self.points} points'
