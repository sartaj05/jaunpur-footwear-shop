from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under review'),
        ('awaiting_customer', 'Waiting for customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    CATEGORY_CHOICES = [
        ('order', 'Order'),
        ('delivery', 'Delivery'),
        ('payment', 'Payment'),
        ('return', 'Return or exchange'),
        ('shop', 'Jaunpur shop'),
        ('other', 'Other'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, blank=True, null=True, related_name='support_tickets')
    shop = models.ForeignKey('shops.Shop', on_delete=models.SET_NULL, blank=True, null=True, related_name='support_tickets')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='assigned_support_tickets')
    subject = models.CharField(max_length=140)
    category = models.CharField(max_length=12, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']

    def __str__(self):
        return f'#{self.pk} {self.subject}'


class SupportMessage(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='support_messages')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'Ticket #{self.ticket_id} · {self.author or "Deleted user"}'
