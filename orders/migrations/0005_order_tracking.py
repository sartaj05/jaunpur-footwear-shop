from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_delivery_rates'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('packed', 'Packed'), ('shipped', 'Shipped'), ('out_for_delivery', 'Out for delivery'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='pending', max_length=20),
        ),
        migrations.CreateModel(
            name='OrderTrackingEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('packed', 'Packed'), ('shipped', 'Shipped'), ('out_for_delivery', 'Out for delivery'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], max_length=20)),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tracking_events', to='orders.order')),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
