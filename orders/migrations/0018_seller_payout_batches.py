import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0017_order_cancellation_refund_tracking'),
        ('shops', '0020_ondc_connection_check'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerPayoutBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_code', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('status', models.CharField(choices=[('prepared', 'Prepared'), ('paid', 'Transfer recorded'), ('cancelled', 'Cancelled')], default='prepared', max_length=10)),
                ('total_amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=12)),
                ('transfer_reference', models.CharField(blank=True, max_length=120)),
                ('staff_note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_seller_payout_batches', to=settings.AUTH_USER_MODEL)),
                ('paid_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_seller_payout_batches', to=settings.AUTH_USER_MODEL)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payout_batches', to='shops.shop')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='SellerPayoutBatchItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sales_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('commission_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('return_adjustment', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
                ('payout_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.sellerpayoutbatch')),
                ('seller_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payout_batch_items', to='orders.sellerorder')),
            ],
            options={'ordering': ['seller_order__created_at', 'seller_order_id']},
        ),
        migrations.AddConstraint(
            model_name='sellerpayoutbatchitem',
            constraint=models.UniqueConstraint(fields=('batch', 'seller_order'), name='unique_seller_order_per_payout_batch'),
        ),
    ]
