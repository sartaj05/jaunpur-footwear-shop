from django.contrib import admin
from .models import CartItem, Coupon, DeliveryRate, Order, OrderItem, OrderTrackingEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderTrackingEventInline(admin.TabularInline):
    model = OrderTrackingEvent
    extra = 0
    readonly_fields = ['created_at', 'created_by']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'mobile', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'mobile']
    inlines = [OrderItemInline, OrderTrackingEventInline]


admin.site.register(CartItem)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'used_count', 'usage_limit', 'is_active']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']


@admin.register(DeliveryRate)
class DeliveryRateAdmin(admin.ModelAdmin):
    list_display = ['pincode_prefix', 'fee', 'free_delivery_minimum', 'is_active']
    list_filter = ['is_active']
    search_fields = ['pincode_prefix']
