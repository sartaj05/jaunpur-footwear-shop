from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('orders', '0014_payment_webhook_event')]

    operations = [
        migrations.CreateModel(
            name='ReturnRefundAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount_subunits', models.PositiveBigIntegerField()),
                ('status', models.CharField(choices=[('queued', 'Queued'), ('processing', 'Processing'), ('submitted', 'Refund submitted to provider'), ('review_required', 'Manual review required')], default='queued', max_length=20)),
                ('provider_refund_id', models.CharField(blank=True, max_length=120)),
                ('error_summary', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('return_request', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='refund_attempt', to='orders.returnrequest')),
            ],
        ),
    ]
