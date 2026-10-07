from django.contrib import admin
from .models import BackgroundJobRun, RecoveryCheck, StaffActionAudit, SystemAlert


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


@admin.register(SystemAlert)
class SystemAlertAdmin(admin.ModelAdmin):
    list_display = ['severity', 'title', 'source', 'state', 'first_seen_at', 'last_seen_at']
    list_filter = ['severity', 'source', 'state']
    search_fields = ['title', 'details', 'dedupe_key']
    readonly_fields = ['dedupe_key', 'source', 'severity', 'title', 'details', 'first_seen_at', 'last_seen_at']


@admin.register(RecoveryCheck)
class RecoveryCheckAdmin(admin.ModelAdmin):
    list_display = ['check_type', 'status', 'checked_by', 'checked_at']
    list_filter = ['check_type', 'status', 'checked_at']
    readonly_fields = ['check_type', 'status', 'details', 'checked_by', 'checked_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
