from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('orders', '0013_return_exchange_workflow')]

    operations = [
        migrations.CreateModel(
            name='PaymentWebhookEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(max_length=160, unique=True)),
                ('event_type', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('received', 'Received'), ('processed', 'Processed'), ('failed', 'Failed')], default='received', max_length=12)),
                ('error_summary', models.CharField(blank=True, max_length=240)),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ['-received_at']},
        ),
    ]
