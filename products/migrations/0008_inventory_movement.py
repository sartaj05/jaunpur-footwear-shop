from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('products', '0007_product_seller_sku'),
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delta', models.IntegerField()),
                ('stock_after', models.PositiveIntegerField()),
                ('reason', models.CharField(default='stock_update', max_length=40)),
                ('reference', models.CharField(blank=True, max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inventory_movements', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='inventory_movements', to='products.product')),
                ('variant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='inventory_movements', to='products.productvariant')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddIndex(
            model_name='inventorymovement',
            index=models.Index(fields=['product', '-created_at'], name='inventory_product_created_idx'),
        ),
    ]
