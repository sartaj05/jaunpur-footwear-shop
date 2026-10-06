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

    def __str__(self):
        return self.user.username


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
