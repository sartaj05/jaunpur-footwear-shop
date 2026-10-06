import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
        ('products', '0002_productvariant'),
    ]

    operations = [
        migrations.AddField(
            model_name='cartitem',
            name='color',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.AddField(
            model_name='cartitem',
            name='variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='products.productvariant'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='color',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
    ]
