from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('orders', '0019_notification_delivery_center')]

    operations = [
        migrations.AddField(
            model_name='sellerorder',
            name='delivered_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
