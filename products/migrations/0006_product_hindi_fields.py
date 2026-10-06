from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0005_product_shop'),
        ('shops', '0007_shop_commission_rate'),
    ]

    operations = [
        migrations.AddField('product', 'name_hi', models.CharField(blank=True, max_length=200)),
        migrations.AddField('product', 'description_hi', models.TextField(blank=True)),
    ]
