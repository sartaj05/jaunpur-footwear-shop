from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_coupon_support'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_pincode',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.CreateModel(
            name='DeliveryRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pincode_prefix', models.CharField(max_length=10, unique=True)),
                ('fee', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=8)),
                ('free_delivery_minimum', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
    ]
