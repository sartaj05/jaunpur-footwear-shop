from django.contrib import admin

from .models import Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'city', 'pincode', 'status', 'created_at']
    list_filter = ['status', 'city', 'created_at']
    search_fields = ['name', 'owner__username', 'phone', 'pincode']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_shops', 'reject_shops']

    @admin.action(description='Approve selected shops')
    def approve_shops(self, request, queryset):
        queryset.update(status='approved')

    @admin.action(description='Reject selected shops')
    def reject_shops(self, request, queryset):
        queryset.update(status='rejected')
