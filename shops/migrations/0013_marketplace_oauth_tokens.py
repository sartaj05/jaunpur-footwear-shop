from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0012_shop_promotion_target_pincodes'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketplaceconnection',
            name='authorization_status',
            field=models.CharField(choices=[('not_connected', 'Not connected'), ('connected', 'Seller authorized'), ('reauthorization_required', 'Reauthorization required')], default='not_connected', max_length=24),
        ),
        migrations.AddField(
            model_name='marketplaceconnection',
            name='encrypted_access_token',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='marketplaceconnection',
            name='encrypted_refresh_token',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='marketplaceconnection',
            name='token_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='marketplaceconnection',
            name='authorized_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
