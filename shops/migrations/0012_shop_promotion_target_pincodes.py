from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shops', '0011_marketplace_product_mapping')]

    operations = [
        migrations.AddField('shoppromotion', 'target_pincodes', models.CharField(blank=True, max_length=700)),
    ]
