from django.contrib import admin
from .models import StaffActionAudit


@admin.register(StaffActionAudit)
class StaffActionAuditAdmin(admin.ModelAdmin):
    list_display = ["actor", "method", "route_name", "response_status", "created_at"]
    list_filter = ["method", "response_status", "created_at"]
    search_fields = ["actor__username", "route_name"]
    readonly_fields = ["actor", "route_name", "method", "response_status", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
