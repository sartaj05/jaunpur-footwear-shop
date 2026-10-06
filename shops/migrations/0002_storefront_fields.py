from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shops', '0001_initial')]

    operations = [
        migrations.AddField('shop', 'description', models.TextField(blank=True)),
        migrations.AddField('shop', 'opening_hours', models.CharField(blank=True, max_length=180)),
        migrations.AddField('shop', 'logo', models.ImageField(blank=True, null=True, upload_to='shops/logos/')),
        migrations.AddField('shop', 'banner', models.ImageField(blank=True, null=True, upload_to='shops/banners/')),
        migrations.AddField('shop', 'is_featured', models.BooleanField(default=False)),
    ]
