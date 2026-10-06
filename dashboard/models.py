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
