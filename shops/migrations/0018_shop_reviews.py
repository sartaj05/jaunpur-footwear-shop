from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0015_return_refund_attempt'),
        ('shops', '0017_shop_coverage_delivery_eta'),
    ]
    operations = [
        migrations.CreateModel(
            name='ShopReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField()),
                ('body', models.TextField(blank=True, max_length=1200)),
                ('is_visible', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shop_reviews', to=settings.AUTH_USER_MODEL)),
                ('seller_order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='shop_review', to='orders.sellerorder')),
                ('shop', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='shops.shop')),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddConstraint(
            model_name='shopreview',
            constraint=models.CheckConstraint(condition=models.Q(('rating__gte', 1), ('rating__lte', 5)), name='shop_review_rating_1_to_5'),
        ),
    ]
