from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_customer_address_book'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerprofile',
            name='email_order_updates',
            field=models.BooleanField(default=True),
        ),
    ]
