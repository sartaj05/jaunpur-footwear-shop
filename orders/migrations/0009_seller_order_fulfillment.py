import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0008_seller_orders'),
        ('shops', '0004_fulfillment_slots'),
    ]

    operations = [
        migrations.AddField('sellerorder', 'shipping_amount', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
        migrations.AddField('sellerorder', 'fulfillment_method', models.CharField(choices=[('delivery', 'Local delivery'), ('pickup', 'Shop pickup')], default='delivery', max_length=10)),
        migrations.AddField('sellerorder', 'fulfillment_date', models.DateField(blank=True, null=True)),
        migrations.AddField('sellerorder', 'fulfillment_slot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seller_orders', to='shops.shopfulfillmentslot')),
    ]
