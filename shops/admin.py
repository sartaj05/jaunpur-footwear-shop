from django.contrib import admin

from .models import Shop, ShopCoverage


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'city', 'pincode', 'status', 'is_featured', 'created_at']
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
