import django.db.models.deletion
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0014_amazon_marketplace_ids'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketplaceproductmapping',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='marketplace_mappings', to='products.product'),
        ),
        migrations.AlterField(
            model_name='marketplaceproductmapping',
            name='variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='marketplace_mappings', to='products.productvariant'),
        ),
        migrations.AddField(
            model_name='marketplaceconnection',
            name='refresh_token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='marketplaceconnection',
            name='fulfillment_location_id',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='marketplaceproductmapping',
            name='allocated_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='MarketplaceSyncRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('running', 'Running'), ('succeeded', 'Succeeded'), ('failed', 'Failed')], default='running', max_length=12)),
                ('orders_seen', models.PositiveIntegerField(default=0)),
                ('order_items_seen', models.PositiveIntegerField(default=0)),
                ('inventory_updates', models.PositiveIntegerField(default=0)),
                ('error_summary', models.TextField(blank=True)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('connection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sync_runs', to='shops.marketplaceconnection')),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='MarketplaceChannelOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_order_id', models.CharField(max_length=160)),
                ('marketplace_id', models.CharField(blank=True, max_length=40)),
                ('external_status', models.CharField(blank=True, max_length=80)),
                ('purchased_at', models.DateTimeField(blank=True, null=True)),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('marketplace_fee', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('settlement_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('settlement_reference', models.CharField(blank=True, max_length=160)),
                ('reconciliation_status', models.CharField(choices=[('open', 'Needs reconciliation'), ('reconciled', 'Reconciled')], default='open', max_length=12)),
                ('reconciled_at', models.DateTimeField(blank=True, null=True)),
                ('last_synced_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('connection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='channel_orders', to='shops.marketplaceconnection')),
            ],
            options={'ordering': ['-purchased_at', '-created_at']},
        ),
        migrations.AddConstraint(
            model_name='marketplacechannelorder',
            constraint=models.UniqueConstraint(fields=('connection', 'external_order_id'), name='unique_marketplace_channel_order'),
        ),
        migrations.CreateModel(
            name='MarketplaceChannelOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_item_id', models.CharField(max_length=160)),
                ('external_sku', models.CharField(blank=True, max_length=120)),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('unit_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('external_status', models.CharField(blank=True, max_length=80)),
                ('inventory_status', models.CharField(choices=[('pending', 'Pending inventory reservation'), ('reserved', 'Reserved from shared stock'), ('shortage', 'Stock shortage'), ('unmapped', 'SKU needs mapping'), ('released', 'Reservation released'), ('sold', 'Fulfilled from reserved stock')], default='pending', max_length=12)),
                ('consumed_quantity', models.PositiveIntegerField(default=0)),
                ('allocation_consumed_quantity', models.PositiveIntegerField(default=0)),
                ('allocation_processed_quantity', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('mapping', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='channel_order_items', to='shops.marketplaceproductmapping')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='shops.marketplacechannelorder')),
            ],
            options={'ordering': ['id']},
        ),
        migrations.AddConstraint(
            model_name='marketplacechannelorderitem',
            constraint=models.UniqueConstraint(fields=('order', 'external_item_id'), name='unique_marketplace_channel_order_item'),
        ),
    ]
