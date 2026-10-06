from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('products', '0008_inventory_movement')]
    operations = [
        migrations.AddField('product', 'low_stock_threshold', models.PositiveIntegerField(default=5)),
        migrations.AddField('productvariant', 'low_stock_threshold', models.PositiveIntegerField(default=5)),
    ]
