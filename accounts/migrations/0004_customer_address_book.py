from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0003_loyalty_and_whatsapp_preferences'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(default='Home', max_length=40)),
                ('recipient_name', models.CharField(max_length=150)),
                ('mobile', models.CharField(max_length=18)),
                ('address', models.TextField(max_length=1000)),
                ('city', models.CharField(default='Jaunpur', max_length=100)),
                ('pincode', models.CharField(max_length=6)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_addresses', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-is_default', 'label', 'id']},
        ),
    ]
