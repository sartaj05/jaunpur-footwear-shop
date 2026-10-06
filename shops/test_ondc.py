from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ONDCEnrollment, Shop


class SuccessfulParticipantAdapter:
    def check_connection(self, enrollment):
        return True


class FailedParticipantAdapter:
    def check_connection(self, enrollment):
        raise RuntimeError('sensitive provider response must not reach seller UI')


class ONDCParticipantConnectionCheckTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='ondc-owner', password='owner-password')
        self.shop = Shop.objects.create(
            owner=self.owner, name='Jaunpur ONDC Shoes', phone='9000000000',
            address='Jaunpur market', pincode='222001', status='approved',
        )
        self.enrollment = ONDCEnrollment.objects.create(
            shop=self.shop, participant_name='Jaunpur SNP', participant_contact='snp@example.test',
            status='partner_confirmed', participant_supports_retail=True,
        )
        self.client.force_login(self.owner)

    @override_settings(ONDC_PARTICIPANT_ADAPTER='shops.test_ondc.SuccessfulParticipantAdapter')
    def test_configured_adapter_can_confirm_connection(self):
        response = self.client.post(reverse('check_ondc_participant_connection'))

        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.participant_connection_status, 'connected')
        self.assertIsNotNone(self.enrollment.participant_connection_checked_at)

    @override_settings(ONDC_PARTICIPANT_ADAPTER='')
    def test_missing_adapter_records_no_network_request(self):
        response = self.client.post(reverse('check_ondc_participant_connection'))

        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.participant_connection_status, 'not_configured')
        self.assertIn('No participant-specific', self.enrollment.participant_connection_note)

    @override_settings(ONDC_PARTICIPANT_ADAPTER='shops.test_ondc.FailedParticipantAdapter')
    def test_adapter_exception_is_safely_reported(self):
        response = self.client.post(reverse('check_ondc_participant_connection'))

        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.participant_connection_status, 'failed')
        self.assertNotIn('sensitive provider response', self.enrollment.participant_connection_note)

    @override_settings(ONDC_PARTICIPANT_ADAPTER='shops.test_ondc.SuccessfulParticipantAdapter')
    def test_unconfirmed_participant_cannot_run_connection_check(self):
        self.enrollment.participant_supports_retail = False
        self.enrollment.save(update_fields=['participant_supports_retail'])

        response = self.client.post(reverse('check_ondc_participant_connection'))

        self.assertEqual(response.status_code, 302)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.participant_connection_status, 'not_configured')
        self.assertIsNone(self.enrollment.participant_connection_checked_at)
