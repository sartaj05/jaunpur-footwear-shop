import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0008_shop_hindi_description'),
        ('products', '0006_product_hindi_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShopPromotion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=140)),
                ('title_hi', models.CharField(blank=True, max_length=140)),
                ('description', models.TextField(blank=True)),
                ('description_hi', models.TextField(blank=True)),
                ('discount_type', models.CharField(choices=[('percent', 'Percentage'), ('fixed', 'Fixed amount')], default='percent', max_length=10)),
                ('discount_value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('products', models.ManyToManyField(related_name='promotions', to='products.product')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotions', to='shops.shop')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
