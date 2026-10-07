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


class SystemAlert(models.Model):
    SEVERITY_CHOICES = [('warning', 'Warning'), ('critical', 'Critical')]
    STATE_CHOICES = [('open', 'Open'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved')]

    dedupe_key = models.CharField(max_length=220, unique=True)
    source = models.CharField(max_length=24)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='warning')
    title = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    state = models.CharField(max_length=14, choices=STATE_CHOICES, default='open')
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='acknowledged_system_alerts')
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='resolved_system_alerts')
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ['state', '-last_seen_at', '-id']

    def __str__(self):
        return f'{self.get_severity_display()}: {self.title}'


class RecoveryCheck(models.Model):
    CHECK_CHOICES = [
        ('database_restore', 'Database restore drill'),
        ('media_restore', 'Media restore drill'),
        ('payment_reconciliation', 'Payment reconciliation'),
    ]
    STATUS_CHOICES = [('passed', 'Passed'), ('failed', 'Failed')]

    check_type = models.CharField(max_length=32, choices=CHECK_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    details = models.TextField(max_length=2000)
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='recovery_checks')
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checked_at', '-id']

    def __str__(self):
        return f'{self.get_check_type_display()} · {self.get_status_display()}'
