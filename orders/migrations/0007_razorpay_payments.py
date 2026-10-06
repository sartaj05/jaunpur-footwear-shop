from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0006_return_requests'),
        ('products', '0002_productvariant'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_status',
            field=models.CharField(choices=[('unpaid', 'Unpaid'), ('pending', 'Payment pending'), ('paid', 'Paid'), ('failed', 'Failed')], default='unpaid', max_length=12),
        ),
        migrations.AddField(
            model_name='order',
            name='stock_released',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_items', to='products.product'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_items', to='products.productvariant'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='used_variant',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='PaymentAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(default='razorpay', max_length=20)),
                ('gateway_order_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('gateway_payment_id', models.CharField(blank=True, max_length=100)),
                ('amount_subunits', models.PositiveBigIntegerField()),
                ('currency', models.CharField(default='INR', max_length=3)),
                ('status', models.CharField(choices=[('created', 'Created'), ('paid', 'Paid'), ('failed', 'Failed')], default='created', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_attempts', to='orders.order')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
