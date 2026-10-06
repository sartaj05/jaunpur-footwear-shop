from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_check_reports_database_availability(self):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch("footwear.health.connection.cursor", side_effect=DatabaseError("private database detail"))
    def test_health_check_hides_database_error_details(self, _cursor):
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotContains(response, "private database detail", status_code=503)

    def test_health_check_accepts_only_get(self):
        self.assertEqual(self.client.post(reverse("health_check")).status_code, 405)
