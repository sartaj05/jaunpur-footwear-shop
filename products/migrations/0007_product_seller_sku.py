from django.db import migrations, models


def assign_existing_seller_skus(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    ProductVariant = apps.get_model('products', 'ProductVariant')
    for product in list(Product.objects.filter(shop__isnull=False, seller_sku__isnull=True)):
        Product.objects.filter(pk=product.pk).update(seller_sku=f'JFW-S{product.shop_id}-P{product.pk}')
    products = dict(Product.objects.filter(shop__isnull=False).values_list('pk', 'seller_sku'))
    for variant_id, product_id, size, color in ProductVariant.objects.filter(seller_sku__isnull=True).values_list('pk', 'product_id', 'size', 'color').iterator():
        product_sku = products.get(product_id)
        if product_sku:
            safe_color = ''.join(character for character in color.upper() if character.isalnum())[:24] or 'COLOR'
            ProductVariant.objects.filter(pk=variant_id).update(seller_sku=f'{product_sku}-{size}-{safe_color}-V{variant_id}'[:120])


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0006_product_hindi_fields'),
        ('shops', '0010_shop_verification'),
    ]

    operations = [
        migrations.AddField('product', 'seller_sku', models.CharField(blank=True, max_length=64, null=True, unique=True)),
        migrations.AddField('productvariant', 'seller_sku', models.CharField(blank=True, max_length=120, null=True, unique=True)),
        migrations.RunPython(assign_existing_seller_skus, migrations.RunPython.noop),
    ]
