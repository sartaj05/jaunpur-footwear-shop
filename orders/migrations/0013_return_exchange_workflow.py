from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('orders', '0012_delivery_dispatch')]

    operations = [
        migrations.AddField('returnrequest', 'exchange_size', models.CharField(blank=True, max_length=10)),
        migrations.AddField('returnrequest', 'pickup_required', models.BooleanField(default=True)),
        migrations.AddField('returnrequest', 'pickup_scheduled_at', models.DateTimeField(blank=True, null=True)),
        migrations.AddField('returnrequest', 'refund_status', models.CharField(choices=[('not_applicable', 'Not applicable'), ('pending', 'Refund pending'), ('processed', 'Refund recorded as sent')], default='not_applicable', max_length=16)),
        migrations.AddField('returnrequest', 'refund_reference', models.CharField(blank=True, max_length=120)),
    ]
