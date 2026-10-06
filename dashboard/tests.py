from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import StaffActionAudit


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
