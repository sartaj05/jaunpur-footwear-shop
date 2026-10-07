from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0020_ondc_connection_check'),
        ('support', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportticket',
            name='shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='support_tickets', to='shops.shop'),
        ),
    ]
