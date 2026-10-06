from django.core.management.base import BaseCommand

from shops.marketplace_sync import sync_marketplace_connection
from shops.models import MarketplaceConnection


class Command(BaseCommand):
    help = 'Import authorized Amazon/Flipkart seller orders and update allocated listing stock.'

    def add_arguments(self, parser):
        parser.add_argument('--shop-id', type=int, help='Sync one Jaunpur shop by database ID.')
        parser.add_argument('--channel', choices=['amazon', 'flipkart'], help='Sync only one marketplace channel.')

    def handle(self, *args, **options):
        connections = MarketplaceConnection.objects.filter(
            status='approved',
            authorization_status='connected',
        ).select_related('shop').order_by('shop_id', 'channel')
        if options.get('shop_id'):
            connections = connections.filter(shop_id=options['shop_id'])
        if options.get('channel'):
            connections = connections.filter(channel=options['channel'])
        connection_ids = list(connections.values_list('pk', flat=True))
        if not connection_ids:
            self.stdout.write(self.style.WARNING('No approved, authorized marketplace connections matched.'))
            return

        failed = 0
        for connection in MarketplaceConnection.objects.filter(pk__in=connection_ids).select_related('shop').order_by('shop_id', 'channel'):
            run = sync_marketplace_connection(connection)
            summary = (
                f'{connection.shop.name} / {connection.get_channel_display()}: {run.get_status_display()}, '
                f'{run.orders_seen} orders, {run.order_items_seen} items, {run.inventory_updates} stock updates.'
            )
            if run.error_summary:
                summary += f' {run.error_summary[:350]}'
            self.stdout.write(self.style.SUCCESS(summary) if run.status == 'succeeded' else self.style.ERROR(summary))
            failed += run.status != 'succeeded'
        if failed:
            self.stderr.write(self.style.ERROR(f'{failed} marketplace connection(s) need attention.'))
