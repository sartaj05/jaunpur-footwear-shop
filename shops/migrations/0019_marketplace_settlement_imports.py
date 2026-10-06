from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shops', '0018_shop_reviews'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketplaceSettlementImport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_filename', models.CharField(max_length=180)),
                ('rows_seen', models.PositiveIntegerField(default=0)),
                ('rows_updated', models.PositiveIntegerField(default=0)),
                ('rows_failed', models.PositiveIntegerField(default=0)),
                ('error_summary', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('connection', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='settlement_imports', to='shops.marketplaceconnection')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marketplace_settlement_imports', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.CreateModel(
            name='MarketplaceSettlementLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_order_id', models.CharField(blank=True, max_length=160)),
                ('marketplace_fee', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('settlement_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('settlement_reference', models.CharField(blank=True, max_length=160)),
                ('status', models.CharField(choices=[('matched', 'Order matched'), ('missing_order', 'Order not found'), ('invalid', 'Invalid row')], max_length=16)),
                ('error_summary', models.CharField(blank=True, max_length=240)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='settlement_lines', to='shops.marketplacechannelorder')),
                ('settlement_import', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='shops.marketplacesettlementimport')),
            ],
            options={'ordering': ['id']},
        ),
    ]
