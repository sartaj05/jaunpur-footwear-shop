from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shops', '0006_ondc_enrollment')]

    operations = [
        migrations.AddField(
            model_name='shop',
            name='commission_rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('10.00'), max_digits=5),
        ),
        migrations.AddConstraint(
            model_name='shop',
            constraint=models.CheckConstraint(
                condition=models.Q(('commission_rate__gte', 0)) & models.Q(('commission_rate__lte', 100)),
                name='shop_commission_between_zero_and_hundred',
            ),
        ),
    ]
