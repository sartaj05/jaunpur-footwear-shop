from django.contrib import admin
from .models import CustomerAddress, CustomerProfile, LoyaltyAccount, LoyaltyTransaction, ReferralCode, ReferralReward


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'mobile', 'city', 'pincode', 'preferred_language', 'whatsapp_order_updates']
    list_filter = ['city', 'preferred_language', 'whatsapp_order_updates']
    search_fields = ['user__username', 'mobile']


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ['label', 'recipient_name', 'user', 'city', 'pincode', 'is_default']
    list_filter = ['city', 'pincode', 'is_default']
    search_fields = ['recipient_name', 'user__username', 'mobile', 'pincode', 'address']


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at']
    search_fields = ['user__username', 'code']


@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referred_user', 'amount', 'status', 'reward_coupon_code', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['referrer__username', 'referred_user__username', 'reward_coupon_code']


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'points', 'updated_at']
    search_fields = ['user__username', 'user__email']


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'transaction_type', 'points', 'order', 'coupon_code', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['account__user__username', 'coupon_code', 'note']
    readonly_fields = ['created_at']
