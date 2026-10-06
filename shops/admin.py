from django.contrib import admin

from .models import MarketplaceConnection, ONDCEnrollment, Shop, ShopCoverage, ShopFulfillmentSlot, ShopPromotion


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'city', 'pincode', 'status', 'commission_rate', 'is_featured', 'created_at']
    list_filter = ['status', 'city', 'is_featured', 'created_at']
    search_fields = ['name', 'owner__username', 'phone', 'pincode']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_shops', 'reject_shops']

    @admin.action(description='Approve selected shops')
    def approve_shops(self, request, queryset):
        queryset.update(status='approved')

    @admin.action(description='Reject selected shops')
    def reject_shops(self, request, queryset):
        queryset.update(status='rejected')


@admin.register(ShopCoverage)
class ShopCoverageAdmin(admin.ModelAdmin):
    list_display = ['shop', 'area_name', 'pincode', 'delivery_fee', 'is_active']
    list_filter = ['is_active', 'pincode']
    search_fields = ['shop__name', 'area_name', 'pincode']


@admin.register(ShopFulfillmentSlot)
class ShopFulfillmentSlotAdmin(admin.ModelAdmin):
    list_display = ['shop', 'mode', 'weekday', 'start_time', 'end_time', 'is_active']
    list_filter = ['mode', 'weekday', 'is_active']
    search_fields = ['shop__name']


@admin.register(MarketplaceConnection)
class MarketplaceConnectionAdmin(admin.ModelAdmin):
    list_display = ['shop', 'channel', 'seller_account_id', 'status', 'requested_at', 'updated_at']
    list_filter = ['channel', 'status', 'requested_at']
    search_fields = ['shop__name', 'seller_account_id']
    readonly_fields = ['requested_at', 'updated_at']


@admin.register(ONDCEnrollment)
class ONDCEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['shop', 'participant_name', 'seller_network_id', 'status', 'submitted_at']
    list_filter = ['status', 'submitted_at']
    search_fields = ['shop__name', 'participant_name', 'seller_network_id', 'application_reference']
    readonly_fields = ['submitted_at', 'updated_at']


@admin.register(ShopPromotion)
class ShopPromotionAdmin(admin.ModelAdmin):
    list_display = ['title', 'shop', 'discount_type', 'discount_value', 'is_active', 'starts_at', 'expires_at']
    list_filter = ['is_active', 'discount_type', 'starts_at', 'expires_at']
    search_fields = ['title', 'shop__name']
    filter_horizontal = ['products']
