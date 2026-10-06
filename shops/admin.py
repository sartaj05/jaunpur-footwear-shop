from django import forms
from django.contrib import admin

from .models import MarketplaceChannelOrder, MarketplaceChannelOrderItem, MarketplaceConnection, MarketplaceProductMapping, MarketplaceSettlementImport, MarketplaceSettlementLine, MarketplaceSyncRun, ONDCEnrollment, Shop, ShopCoverage, ShopFulfillmentSlot, ShopPromotion, ShopReview


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'city', 'pincode', 'status', 'verification_status', 'commission_rate', 'is_featured', 'created_at']
    list_filter = ['status', 'verification_status', 'city', 'is_featured', 'created_at']
    search_fields = ['name', 'owner__username', 'phone', 'pincode']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_shops', 'reject_shops', 'verify_shops', 'request_verification_changes']

    @admin.action(description='Approve selected shops')
    def approve_shops(self, request, queryset):
        queryset.update(status='approved')

    @admin.action(description='Reject selected shops')
    def reject_shops(self, request, queryset):
        queryset.update(status='rejected')

    @admin.action(description='Verify selected Jaunpur shops')
    def verify_shops(self, request, queryset):
        from django.utils import timezone

        queryset.update(verification_status='verified', verified_at=timezone.now(), verified_by=request.user, verification_note='')

    @admin.action(description='Request more verification information')
    def request_verification_changes(self, request, queryset):
        queryset.update(verification_status='needs_changes', verified_at=None, verified_by=None)


@admin.register(ShopCoverage)
class ShopCoverageAdmin(admin.ModelAdmin):
    list_display = ['shop', 'area_name', 'pincode', 'delivery_fee', 'min_delivery_days', 'max_delivery_days', 'is_active']
    list_filter = ['is_active', 'pincode']
    search_fields = ['shop__name', 'area_name', 'pincode']


@admin.register(ShopFulfillmentSlot)
class ShopFulfillmentSlotAdmin(admin.ModelAdmin):
    list_display = ['shop', 'mode', 'weekday', 'start_time', 'end_time', 'is_active']
    list_filter = ['mode', 'weekday', 'is_active']
    search_fields = ['shop__name']


@admin.register(MarketplaceConnection)
class MarketplaceConnectionAdmin(admin.ModelAdmin):
    list_display = ['shop', 'channel', 'seller_account_id', 'status', 'authorization_status', 'requested_at', 'updated_at']
    list_filter = ['channel', 'status', 'requested_at']
    search_fields = ['shop__name', 'seller_account_id']
    readonly_fields = ['requested_at', 'updated_at', 'authorization_status', 'token_expires_at', 'authorized_at']
    exclude = ['encrypted_access_token', 'encrypted_refresh_token']


@admin.register(ONDCEnrollment)
class ONDCEnrollmentAdmin(admin.ModelAdmin):
    class Form(forms.ModelForm):
        class Meta:
            model = ONDCEnrollment
            fields = '__all__'

        def clean(self):
            cleaned = super().clean()
            if cleaned.get('status') == 'live':
                if not cleaned.get('participant_supports_retail'):
                    self.add_error('participant_supports_retail', 'Confirm that this participant supports the ONDC retail domain before marking production live.')
                if not cleaned.get('participant_seller_id') or not cleaned.get('network_subscriber_id'):
                    self.add_error(None, 'Record the participant seller ID and network subscriber ID before marking production live.')
            return cleaned

    form = Form
    list_display = ['shop', 'participant_name', 'seller_network_id', 'participant_supports_retail', 'status', 'submitted_at']
    list_filter = ['status', 'submitted_at']
    search_fields = ['shop__name', 'participant_name', 'seller_network_id', 'participant_seller_id', 'network_subscriber_id', 'application_reference']
    readonly_fields = ['submitted_at', 'catalog_exported_at', 'production_activated_at', 'updated_at']

    def save_model(self, request, obj, form, change):
        from django.utils import timezone

        if obj.status == 'live' and not obj.production_activated_at:
            obj.production_activated_at = timezone.now()
        elif obj.status != 'live':
            obj.production_activated_at = None
        super().save_model(request, obj, form, change)


@admin.register(ShopPromotion)
class ShopPromotionAdmin(admin.ModelAdmin):
    list_display = ['title', 'shop', 'discount_type', 'discount_value', 'is_active', 'starts_at', 'expires_at']
    list_filter = ['is_active', 'discount_type', 'starts_at', 'expires_at']
    search_fields = ['title', 'shop__name']
    filter_horizontal = ['products']


@admin.register(MarketplaceProductMapping)
class MarketplaceProductMappingAdmin(admin.ModelAdmin):
    list_display = ['connection', 'external_sku', 'product', 'variant', 'allocated_quantity', 'status', 'last_synced_at']
    list_filter = ['connection__channel', 'status']
    search_fields = ['external_sku', 'product__name', 'connection__shop__name']


@admin.register(MarketplaceSyncRun)
class MarketplaceSyncRunAdmin(admin.ModelAdmin):
    list_display = ['connection', 'status', 'orders_seen', 'order_items_seen', 'inventory_updates', 'started_at', 'completed_at']
    list_filter = ['connection__channel', 'status', 'started_at']
    search_fields = ['connection__shop__name', 'error_summary']
    readonly_fields = ['connection', 'status', 'orders_seen', 'order_items_seen', 'inventory_updates', 'error_summary', 'started_at', 'completed_at']


class MarketplaceChannelOrderItemInline(admin.TabularInline):
    model = MarketplaceChannelOrderItem
    extra = 0
    can_delete = False
    readonly_fields = ['external_item_id', 'external_sku', 'mapping', 'quantity', 'unit_price', 'currency', 'external_status', 'inventory_status', 'consumed_quantity']


@admin.register(MarketplaceChannelOrder)
class MarketplaceChannelOrderAdmin(admin.ModelAdmin):
    list_display = ['connection', 'external_order_id', 'external_status', 'total_amount', 'marketplace_fee', 'settlement_amount', 'reconciliation_status', 'purchased_at']
    list_filter = ['connection__channel', 'reconciliation_status', 'external_status', 'purchased_at']
    search_fields = ['external_order_id', 'settlement_reference', 'connection__shop__name']
    readonly_fields = ['connection', 'external_order_id', 'marketplace_id', 'external_status', 'purchased_at', 'currency', 'total_amount', 'created_at', 'last_synced_at']
    inlines = [MarketplaceChannelOrderItemInline]


class MarketplaceSettlementLineInline(admin.TabularInline):
    model = MarketplaceSettlementLine
    extra = 0
    can_delete = False
    readonly_fields = ['order', 'external_order_id', 'marketplace_fee', 'settlement_amount', 'settlement_reference', 'status', 'error_summary', 'created_at']


@admin.register(MarketplaceSettlementImport)
class MarketplaceSettlementImportAdmin(admin.ModelAdmin):
    list_display = ['connection', 'source_filename', 'rows_seen', 'rows_updated', 'rows_failed', 'uploaded_by', 'created_at']
    list_filter = ['connection__channel', 'created_at']
    search_fields = ['source_filename', 'connection__shop__name', 'error_summary']
    readonly_fields = ['connection', 'uploaded_by', 'source_filename', 'rows_seen', 'rows_updated', 'rows_failed', 'error_summary', 'created_at']
    inlines = [MarketplaceSettlementLineInline]


@admin.register(ShopReview)
class ShopReviewAdmin(admin.ModelAdmin):
    list_display = ['shop', 'customer', 'seller_order', 'rating', 'is_visible', 'created_at']
    list_filter = ['rating', 'is_visible', 'created_at']
    search_fields = ['shop__name', 'customer__username', 'body']
    readonly_fields = ['shop', 'customer', 'seller_order', 'rating', 'body', 'created_at', 'updated_at']
