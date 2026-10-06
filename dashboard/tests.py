from django.contrib.auth.models import User
from unittest.mock import Mock

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import StaffActionAudit
from footwear.task_dispatch import dispatch_background_task
from .models import BackgroundJobRun


class StaffActionAuditTests(TestCase):
    def test_successful_staff_write_is_audited(self):
        staff = User.objects.create_user(username="staff", password="test-password", is_staff=True)
        self.client.force_login(staff)

        response = self.client.post(reverse("add_brand"), {"name": "Audit Brand"})

        self.assertEqual(response.status_code, 302)
        event = StaffActionAudit.objects.get()
        self.assertEqual(event.actor, staff)
        self.assertEqual(event.route_name, "add_brand")
        self.assertEqual(event.method, "POST")
        self.assertEqual(event.response_status, 302)


class BackgroundDispatchTests(TestCase):
    @override_settings(CELERY_BROKER_URL="redis://localhost:6379/0")
    def test_queued_task_has_admin_visible_run_record(self):
        task = Mock()
        task.name = "orders.tasks.example"

        run = dispatch_background_task(task, 123)

        self.assertIsInstance(run, BackgroundJobRun)
        self.assertEqual(run.status, "pending")
        task.apply_async.assert_called_once_with(args=(123, run.pk), task_id=str(run.pk))
