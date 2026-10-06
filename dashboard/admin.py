from django.contrib import admin
from .models import BackgroundJobRun, StaffActionAudit


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


@admin.register(BackgroundJobRun)
class BackgroundJobRunAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'status', 'retry_count', 'queued_at', 'started_at', 'finished_at']
    list_filter = ['status', 'queued_at']
    search_fields = ['task_name', 'error_summary']
    readonly_fields = ['task_name', 'status', 'retry_count', 'error_summary', 'queued_at', 'started_at', 'finished_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
