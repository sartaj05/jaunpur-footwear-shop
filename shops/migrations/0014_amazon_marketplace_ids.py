from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0013_marketplace_oauth_tokens'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketplaceconnection',
            name='amazon_marketplace_ids',
            field=models.CharField(blank=True, max_length=700),
        ),
    ]
