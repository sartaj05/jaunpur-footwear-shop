from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0005_customer_email_update_preference'),
        ('orders', '0018_seller_payout_batches'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idempotency_key', models.CharField(max_length=220, unique=True)),
                ('channel', models.CharField(choices=[('email', 'Email'), ('whatsapp', 'WhatsApp')], max_length=10)),
                ('event_type', models.CharField(choices=[('order_confirmation', 'Order confirmation'), ('order_status', 'Order status update')], max_length=24)),
                ('status', models.CharField(choices=[('accepted', 'Accepted by provider'), ('failed', 'Failed'), ('skipped', 'Skipped by preference or setup')], max_length=10)),
                ('summary', models.CharField(max_length=240)),
                ('error_summary', models.CharField(blank=True, max_length=300)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_deliveries', to='orders.order')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_deliveries', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
    ]
