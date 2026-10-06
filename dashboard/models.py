from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class StaffActionAudit(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_action_audits",
    )
    route_name = models.CharField(max_length=160, blank=True)
    method = models.CharField(max_length=8)
    response_status = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.actor or 'Deleted staff'} · {self.method} {self.route_name}"


class BackgroundJobRun(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('running', 'Running'), ('succeeded', 'Succeeded'), ('failed', 'Failed')]

    task_name = models.CharField(max_length=200)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_summary = models.CharField(max_length=300, blank=True)
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-queued_at', '-id']

    def __str__(self):
        return f'{self.task_name} · {self.get_status_display()}'
