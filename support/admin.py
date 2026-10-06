from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import SupportMessage, SupportTicket


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ['author', 'body', 'created_at']
    can_delete = False


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'user', 'category', 'status', 'assigned_to', 'conversation', 'updated_at']
    list_filter = ['status', 'category', 'updated_at']
    search_fields = ['subject', 'user__username', 'user__email', 'order__id']
    list_editable = ['status', 'assigned_to']
    readonly_fields = ['user', 'order', 'subject', 'category', 'description', 'created_at', 'updated_at']
    inlines = [SupportMessageInline]

    @admin.display(description='Conversation')
    def conversation(self, obj):
        return format_html('<a href="{}">Open support conversation</a>', reverse('support_detail', args=[obj.pk]))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'assigned_to':
            kwargs['queryset'] = db_field.remote_field.model.objects.filter(is_staff=True, is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'author', 'created_at']
    search_fields = ['ticket__subject', 'body', 'author__username']
    readonly_fields = ['ticket', 'author', 'body', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
