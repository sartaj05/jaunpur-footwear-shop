from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('shops', '0002_storefront_fields')]

    operations = [
        migrations.CreateModel(
            name='ShopCoverage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pincode', models.CharField(max_length=6)),
                ('area_name', models.CharField(blank=True, max_length=100)),
                ('delivery_fee', models.DecimalField(decimal_places=2, default='50.00', max_digits=8)),
                ('free_delivery_minimum', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coverage_areas', to='shops.shop')),
            ],
            options={'ordering': ['pincode']},
        ),
        migrations.AddConstraint(
            model_name='shopcoverage',
            constraint=models.UniqueConstraint(fields=('shop', 'pincode'), name='unique_shop_coverage_pincode'),
        ),
    ]
