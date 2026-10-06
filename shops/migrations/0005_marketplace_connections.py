from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('shops', '0004_fulfillment_slots')]

    operations = [
        migrations.CreateModel(
            name='MarketplaceConnection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(choices=[('amazon', 'Amazon'), ('flipkart', 'Flipkart')], max_length=12)),
                ('seller_account_id', models.CharField(blank=True, max_length=120)),
                ('status', models.CharField(choices=[('not_requested', 'Not requested'), ('pending', 'Request pending'), ('approved', 'Seller setup approved')], default='not_requested', max_length=16)),
                ('staff_note', models.TextField(blank=True)),
                ('requested_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_connections', to='shops.shop')),
            ],
            options={'ordering': ['channel']},
        ),
        migrations.AddConstraint(
            model_name='marketplaceconnection',
            constraint=models.UniqueConstraint(fields=('shop', 'channel'), name='unique_shop_marketplace_channel'),
        ),
    ]
