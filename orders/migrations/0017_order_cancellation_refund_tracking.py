from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0016_order_stock_reservation_expiry'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment_status',
            field=models.CharField(
                choices=[
                    ('unpaid', 'Unpaid'),
                    ('pending', 'Payment pending'),
                    ('paid', 'Paid'),
                    ('failed', 'Failed'),
                    ('refund_pending', 'Refund pending'),
                    ('refunded', 'Refunded'),
                ],
                default='unpaid',
                max_length=16,
            ),
        ),
        migrations.CreateModel(
            name='OrderCancellationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(max_length=1000)),
                ('status', models.CharField(
                    choices=[
                        ('requested', 'Awaiting staff review'),
                        ('rejected', 'Cancellation declined'),
                        ('cancelled', 'Cancelled'),
                        ('refund_pending', 'Cancelled · refund pending'),
                        ('refunded', 'Cancelled · refund recorded'),
                    ],
                    default='requested',
                    max_length=20,
                )),
                ('staff_note', models.TextField(blank=True)),
                ('refund_reference', models.CharField(blank=True, max_length=120)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('refunded_at', models.DateTimeField(blank=True, null=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_cancellations', to=settings.AUTH_USER_MODEL)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cancellation_request', to='orders.order')),
            ],
            options={'ordering': ['-requested_at', '-id']},
        ),
    ]
