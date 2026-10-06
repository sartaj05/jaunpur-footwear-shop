from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import MarketplaceChannelOrder, MarketplaceConnection, MarketplaceSettlementImport, Shop


class MarketplaceSettlementImportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='settlement-owner', password='owner-password')
        self.shop = Shop.objects.create(
            owner=self.owner, name='Jaunpur Settlement Shoes', phone='9000000000',
            address='Jaunpur market', pincode='222001', status='approved',
        )
        self.connection = MarketplaceConnection.objects.create(
            shop=self.shop, channel='amazon', status='approved',
            authorization_status='connected', seller_account_id='seller-1',
        )
        self.order = MarketplaceChannelOrder.objects.create(
            connection=self.connection, external_order_id='ORDER-100', total_amount=Decimal('2000.00'),
        )

    def upload(self, contents, filename='settlement.csv'):
        self.client.force_login(self.owner)
        return self.client.post(reverse('marketplace_channel_orders'), {
            'action': 'import_settlement_csv',
            'connection_id': str(self.connection.pk),
            'settlement_file': SimpleUploadedFile(filename, contents.encode('utf-8'), content_type='text/csv'),
        })

    def test_import_reconciles_matching_orders_and_retains_row_errors(self):
        response = self.upload(
            'external_order_id,marketplace_fee,settlement_amount,settlement_reference\n'
            'ORDER-100,125.00,1875.00,SETTLE-1\n'
            'OTHER-SELLER-ORDER,20.00,180.00,SETTLE-2\n'
            'ORDER-BAD,NaN,50.00,SETTLE-3\n'
        )

        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.reconciliation_status, 'reconciled')
        self.assertEqual(self.order.marketplace_fee, Decimal('125.00'))
        self.assertEqual(self.order.settlement_amount, Decimal('1875.00'))
        batch = MarketplaceSettlementImport.objects.get(connection=self.connection)
        self.assertEqual((batch.rows_seen, batch.rows_updated, batch.rows_failed), (3, 1, 2))
        self.assertEqual(batch.lines.filter(status='matched').count(), 1)
        self.assertEqual(batch.lines.filter(status='missing_order').count(), 1)
        self.assertEqual(batch.lines.filter(status='invalid').count(), 1)

    def test_import_is_scoped_to_the_selected_connected_seller(self):
        other_owner = User.objects.create_user(username='other-seller', password='owner-password')
        other_shop = Shop.objects.create(
            owner=other_owner, name='Other Seller', phone='9000000002',
            address='Jaunpur', pincode='222002', status='approved',
        )
        other_connection = MarketplaceConnection.objects.create(
            shop=other_shop, channel='amazon', status='approved', authorization_status='connected',
        )
        other_order = MarketplaceChannelOrder.objects.create(
            connection=other_connection, external_order_id='PRIVATE-ORDER',
        )
        self.upload(
            'external_order_id,marketplace_fee,settlement_amount,settlement_reference\n'
            'PRIVATE-ORDER,2.00,98.00,SETTLE-OTHER\n'
        )

        other_order.refresh_from_db()
        batch = MarketplaceSettlementImport.objects.get(connection=self.connection)
        self.assertEqual(other_order.reconciliation_status, 'open')
        self.assertEqual(batch.rows_updated, 0)
        self.assertEqual(batch.rows_failed, 1)
        self.assertEqual(batch.lines.first().status, 'missing_order')

    def test_unapproved_or_unconnected_connection_cannot_receive_upload(self):
        self.connection.authorization_status = 'not_connected'
        self.connection.save(update_fields=['authorization_status'])
        self.client.force_login(self.owner)

        response = self.client.post(reverse('marketplace_channel_orders'), {
            'action': 'import_settlement_csv',
            'connection_id': str(self.connection.pk),
            'settlement_file': SimpleUploadedFile('statement.csv', b'not,a,valid,statement'),
        })

        self.assertEqual(response.status_code, 404)
        self.assertFalse(MarketplaceSettlementImport.objects.exists())
