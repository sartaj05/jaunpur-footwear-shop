import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_referrals'),
        ('orders', '0013_return_exchange_workflow'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField('customerprofile', 'whatsapp_order_updates', models.BooleanField(default=False)),
        migrations.AddField('customerprofile', 'preferred_language', models.CharField(choices=[('en', 'English'), ('hi', 'Hindi')], default='en', max_length=2)),
        migrations.CreateModel(
            name='LoyaltyAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('points', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='loyalty_account', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='LoyaltyTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('earned', 'Points earned'), ('redeemed', 'Points redeemed')], max_length=10)),
                ('points', models.PositiveIntegerField()),
                ('coupon_code', models.CharField(blank=True, max_length=30)),
                ('note', models.CharField(blank=True, max_length=180)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='accounts.loyaltyaccount')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='loyalty_transactions', to='orders.order')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddConstraint('loyaltytransaction', models.UniqueConstraint(condition=models.Q(('order__isnull', False)), fields=('order', 'transaction_type'), name='unique_order_loyalty_transaction')),
    ]
