import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0011_coupon_owner'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryRider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=15)),
                ('home_pincode', models.CharField(blank=True, max_length=6)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_rider_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['user__username']},
        ),
        migrations.CreateModel(
            name='DeliveryRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pincode', models.CharField(max_length=6)),
                ('delivery_date', models.DateField()),
                ('status', models.CharField(choices=[('planned', 'Planned'), ('in_progress', 'In progress'), ('completed', 'Completed')], default='planned', max_length=12)),
                ('route_note', models.CharField(blank=True, max_length=240)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_delivery_runs', to=settings.AUTH_USER_MODEL)),
                ('rider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='runs', to='orders.deliveryrider')),
            ],
            options={'ordering': ['delivery_date', 'pincode', 'id']},
        ),
        migrations.CreateModel(
            name='DeliveryAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence', models.PositiveSmallIntegerField(default=1)),
                ('status', models.CharField(choices=[('assigned', 'Assigned'), ('delivered', 'Delivered')], default='assigned', max_length=12)),
                ('delivered_to', models.CharField(blank=True, max_length=120)),
                ('proof_photo', models.ImageField(blank=True, null=True, upload_to='delivery/proof/')),
                ('note', models.TextField(blank=True)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='orders.deliveryrun')),
                ('seller_order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_assignment', to='orders.sellerorder')),
            ],
            options={'ordering': ['run', 'sequence']},
        ),
        migrations.AddConstraint('deliveryassignment', models.UniqueConstraint(fields=('run', 'sequence'), name='unique_delivery_run_stop_sequence')),
    ]
