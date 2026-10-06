from django.contrib.auth.models import User
from unittest.mock import Mock

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import StaffActionAudit
from footwear.task_dispatch import dispatch_background_task
from .models import BackgroundJobRun
from orders.models import Order
from decimal import Decimal


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

    def test_staff_can_download_period_sales_csv(self):
        staff = User.objects.create_user(username="report-staff", password="test-password", is_staff=True)
        Order.objects.create(
            user=staff, full_name="Report Buyer", mobile="9000000000", address="Jaunpur",
            total_amount=Decimal("100.00"),
        )
        self.client.force_login(staff)

        response = self.client.get(reverse("sales_reports"), {"days": "30", "format": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn(b"Order ID,Created at", response.content)
