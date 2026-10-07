from django.contrib import admin
from django.db import transaction
from django.contrib import messages
from .models import CartItem, Coupon, DeliveryAssignment, DeliveryRate, DeliveryRider, DeliveryRun, Order, OrderItem, OrderTrackingEvent, PaymentAttempt, PaymentWebhookEvent, ReturnRefundAttempt, ReturnRequest, SellerOrder, SellerPayoutBatch, SellerPayoutBatchItem
from .tasks import process_return_refund_task
from footwear.task_dispatch import dispatch_background_task


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
    list_display = ['id', 'user', 'mobile', 'total_amount', 'status', 'payment_status', 'payment_method', 'stock_reservation_expires_at', 'stock_released', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method', 'stock_released', 'created_at']
    readonly_fields = ['stock_reservation_expires_at', 'stock_released']
    search_fields = ['user__username', 'mobile']
    inlines = [OrderItemInline, OrderTrackingEventInline, SellerOrderInline]


admin.site.register(CartItem)


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'event_type', 'status', 'received_at', 'processed_at']
    list_filter = ['status', 'event_type', 'received_at']
    search_fields = ['event_id', 'event_type', 'error_summary']
    readonly_fields = ['event_id', 'event_type', 'status', 'error_summary', 'received_at', 'processed_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


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
    actions = ['queue_razorpay_refunds']
    list_display = ['id', 'order', 'customer', 'request_type', 'status', 'refund_status', 'pickup_scheduled_at', 'refund_action', 'requested_at']
    list_filter = ['request_type', 'status', 'refund_status', 'pickup_required', 'requested_at']
    search_fields = ['order__id', 'customer__username', 'reason', 'refund_reference']

    @admin.display(description='Payment action')
    def refund_action(self, obj):
        if obj.request_type == 'return' and obj.status == 'received' and obj.refund_status == 'pending':
            return 'Select row and choose the refund action'
        if hasattr(obj, 'refund_attempt'):
            return obj.refund_attempt.get_status_display()
        return '—'

    @admin.action(description='Queue verified Razorpay refunds for received returns')
    def queue_razorpay_refunds(self, request, queryset):
        queued = 0
        for row in queryset.select_related('order', 'order_item'):
            with transaction.atomic():
                return_request = ReturnRequest.objects.select_for_update(of=('self',)).select_related('order', 'order_item').get(pk=row.pk)
                eligible = (
                    return_request.request_type == 'return'
                    and return_request.status == 'received'
                    and return_request.refund_status == 'pending'
                    and return_request.order.payment_status == 'paid'
                    and return_request.order_item_id
                    and return_request.order.payment_attempts.filter(status='paid', gateway_payment_id__gt='').exists()
                    and not ReturnRefundAttempt.objects.filter(return_request=return_request).exists()
                )
                if not eligible:
                    continue
                amount_subunits = int(return_request.order_item.price * return_request.order_item.quantity * 100)
                ReturnRefundAttempt.objects.create(return_request=return_request, amount_subunits=amount_subunits)
                transaction.on_commit(lambda return_id=return_request.pk: dispatch_background_task(process_return_refund_task, return_id))
                queued += 1
        if queued:
            self.message_user(request, f'Queued {queued} Razorpay refund job(s). Review their status before responding to customers.', messages.SUCCESS)
        else:
            self.message_user(request, 'No selected return was eligible for a new online refund.', messages.WARNING)


@admin.register(ReturnRefundAttempt)
class ReturnRefundAttemptAdmin(admin.ModelAdmin):
    list_display = ['return_request', 'amount_subunits', 'status', 'provider_refund_id', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['return_request__order_id', 'provider_refund_id', 'error_summary']
    readonly_fields = ['return_request', 'amount_subunits', 'status', 'provider_refund_id', 'error_summary', 'created_at', 'updated_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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


class SellerPayoutBatchItemInline(admin.TabularInline):
    model = SellerPayoutBatchItem
    extra = 0
    readonly_fields = ['seller_order', 'sales_amount', 'commission_amount', 'return_adjustment', 'payout_amount', 'created_at']


@admin.register(SellerPayoutBatch)
class SellerPayoutBatchAdmin(admin.ModelAdmin):
    list_display = ['batch_code', 'shop', 'status', 'total_amount', 'transfer_reference', 'created_by', 'paid_by', 'created_at', 'paid_at']
    list_filter = ['status', 'shop', 'created_at']
    search_fields = ['batch_code', 'shop__name', 'transfer_reference']
    readonly_fields = ['batch_code', 'status', 'total_amount', 'transfer_reference', 'created_by', 'paid_by', 'created_at', 'paid_at']
    inlines = [SellerPayoutBatchItemInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
