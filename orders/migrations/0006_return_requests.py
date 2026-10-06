from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_order_tracking'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReturnRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_type', models.CharField(choices=[('return', 'Return'), ('exchange', 'Exchange')], max_length=10)),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('received', 'Item received'), ('completed', 'Completed')], default='pending', max_length=12)),
                ('staff_note', models.TextField(blank=True)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_requests', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_requests', to='orders.order')),
                ('order_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='return_requests', to='orders.orderitem')),
            ],
            options={
                'ordering': ['-requested_at'],
            },
        ),
    ]
