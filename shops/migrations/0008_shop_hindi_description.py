from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shops', '0007_shop_commission_rate')]

    operations = [
        migrations.AddField('shop', 'description_hi', models.TextField(blank=True)),
    ]
