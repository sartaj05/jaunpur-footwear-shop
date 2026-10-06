from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0009_seller_order_fulfillment'),
        ('shops', '0007_shop_commission_rate'),
    ]

    operations = [
        migrations.AddField('sellerorder', 'sales_amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
        migrations.AddField('sellerorder', 'commission_rate', models.DecimalField(decimal_places=2, default='0.00', max_digits=5)),
        migrations.AddField('sellerorder', 'commission_amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
        migrations.AddField('sellerorder', 'net_amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
        migrations.AddField('sellerorder', 'payout_status', models.CharField(choices=[('pending', 'Pending payout'), ('paid', 'Paid out')], default='pending', max_length=10)),
        migrations.AddField('sellerorder', 'payout_reference', models.CharField(blank=True, max_length=120)),
        migrations.AddField('sellerorder', 'paid_out_at', models.DateTimeField(blank=True, null=True)),
    ]
