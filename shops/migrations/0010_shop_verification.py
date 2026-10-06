import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0009_shop_promotions'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField('shop', 'verification_status', models.CharField(choices=[('not_submitted', 'Not submitted'), ('pending', 'Verification pending'), ('verified', 'Verified Jaunpur shop'), ('needs_changes', 'More information required')], default='not_submitted', max_length=16)),
        migrations.AddField('shop', 'verification_requested_at', models.DateTimeField(blank=True, null=True)),
        migrations.AddField('shop', 'verified_at', models.DateTimeField(blank=True, null=True)),
        migrations.AddField('shop', 'verification_note', models.TextField(blank=True)),
        migrations.AddField('shop', 'verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_jaunpur_shops', to=settings.AUTH_USER_MODEL)),
    ]
