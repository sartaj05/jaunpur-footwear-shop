from django.contrib import admin
from .models import CartItem, Coupon, DeliveryAssignment, DeliveryRate, DeliveryRider, DeliveryRun, Order, OrderItem, OrderTrackingEvent, PaymentAttempt, ReturnRequest, SellerOrder


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderTrackingEventInline(admin.TabularInline):
    model = OrderTrackingEvent
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class SellerOrderInline(admin.TabularInline):
    model = SellerOrder
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'mobile', 'total_amount', 'status', 'payment_status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['user__username', 'mobile']
    inlines = [OrderItemInline, OrderTrackingEventInline, SellerOrderInline]


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


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'customer', 'request_type', 'status', 'requested_at']
    list_filter = ['request_type', 'status', 'requested_at']
    search_fields = ['order__id', 'customer__username', 'reason']


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ['order', 'provider', 'amount_subunits', 'currency', 'status', 'created_at', 'paid_at']
    list_filter = ['provider', 'status', 'created_at']
    search_fields = ['gateway_order_id', 'gateway_payment_id', 'order__id']


@admin.register(SellerOrder)
class SellerOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'shop', 'sales_amount', 'commission_amount', 'net_amount', 'status', 'payout_status', 'created_at']
    list_filter = ['status', 'payout_status', 'created_at']
    search_fields = ['shop__name', 'order__id']


@admin.register(DeliveryRider)
class DeliveryRiderAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'home_pincode', 'is_active']
    list_filter = ['is_active', 'home_pincode']
    search_fields = ['user__username', 'user__first_name', 'phone', 'home_pincode']


@admin.register(DeliveryRun)
class DeliveryRunAdmin(admin.ModelAdmin):
    list_display = ['id', 'delivery_date', 'pincode', 'rider', 'status']
    list_filter = ['status', 'delivery_date', 'pincode']
    search_fields = ['rider__user__username', 'pincode']
    inlines = []


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ['run', 'sequence', 'seller_order', 'status', 'delivered_to', 'delivered_at']
    list_filter = ['status', 'run__delivery_date', 'run__pincode']
    search_fields = ['seller_order__order__id', 'seller_order__shop__name', 'delivered_to']
