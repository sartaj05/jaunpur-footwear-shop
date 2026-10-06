import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0010_shop_verification'),
        ('products', '0007_product_seller_sku'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketplaceProductMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_sku', models.CharField(max_length=120)),
                ('external_listing_id', models.CharField(blank=True, max_length=160)),
                ('category_path', models.CharField(blank=True, max_length=240)),
                ('status', models.CharField(choices=[('draft', 'Draft mapping'), ('submitted', 'Submitted to marketplace'), ('active', 'Active listing'), ('needs_attention', 'Needs attention')], default='draft', max_length=20)),
                ('error_text', models.TextField(blank=True)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('connection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_mappings', to='shops.marketplaceconnection')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_mappings', to='products.product')),
                ('variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='marketplace_mappings', to='products.productvariant')),
            ],
            options={'ordering': ['connection__channel', 'external_sku']},
        ),
        migrations.AddConstraint('marketplaceproductmapping', models.UniqueConstraint(fields=('connection', 'external_sku'), name='unique_channel_external_sku')),
        migrations.AddConstraint('marketplaceproductmapping', models.UniqueConstraint(condition=models.Q(('variant__isnull', True)), fields=('connection', 'product'), name='unique_channel_product_base_mapping')),
        migrations.AddConstraint('marketplaceproductmapping', models.UniqueConstraint(condition=models.Q(('variant__isnull', False)), fields=('connection', 'product', 'variant'), name='unique_channel_product_variant_mapping')),
    ]
