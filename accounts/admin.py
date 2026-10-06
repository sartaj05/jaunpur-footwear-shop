from django.contrib import admin
from .models import CustomerProfile, ReferralCode, ReferralReward


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'mobile', 'city', 'pincode']
    search_fields = ['user__username', 'mobile']


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at']
    search_fields = ['user__username', 'code']


@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referred_user', 'amount', 'status', 'reward_coupon_code', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['referrer__username', 'referred_user__username', 'reward_coupon_code']
