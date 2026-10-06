from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('shops', '0003_shop_coverage')]

    operations = [
        migrations.CreateModel(
            name='ShopFulfillmentSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mode', models.CharField(choices=[('delivery', 'Local delivery'), ('pickup', 'Shop pickup')], max_length=10)),
                ('weekday', models.PositiveSmallIntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('max_orders', models.PositiveSmallIntegerField(default=20)),
                ('is_active', models.BooleanField(default=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fulfillment_slots', to='shops.shop')),
            ],
            options={'ordering': ['weekday', 'start_time']},
        ),
        migrations.AddConstraint(
            model_name='shopfulfillmentslot',
            constraint=models.CheckConstraint(condition=models.Q(('end_time__gt', models.F('start_time'))), name='shop_slot_end_after_start'),
        ),
        migrations.AddConstraint(
            model_name='shopfulfillmentslot',
            constraint=models.CheckConstraint(condition=models.Q(('max_orders__gte', 1)), name='shop_slot_min_capacity_one'),
        ),
    ]
