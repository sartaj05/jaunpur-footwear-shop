from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_cartitem_variants_and_orderitem_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='coupon_code',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='order',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10),
        ),
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=30, unique=True)),
                ('discount_type', models.CharField(choices=[('percent', 'Percentage'), ('fixed', 'Fixed amount')], default='percent', max_length=10)),
                ('discount_value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('minimum_order_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('usage_limit', models.PositiveIntegerField(blank=True, null=True)),
                ('used_count', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
    ]
