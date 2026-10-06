from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('shops', '0005_marketplace_connections')]

    operations = [
        migrations.CreateModel(
            name='ONDCEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('participant_name', models.CharField(blank=True, max_length=160)),
                ('participant_contact', models.CharField(blank=True, max_length=160)),
                ('seller_network_id', models.CharField(blank=True, max_length=120)),
                ('application_reference', models.CharField(blank=True, max_length=120)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Partner request submitted'), ('partner_confirmed', 'Seller Network Participant confirmed'), ('onboarded', 'Seller onboarding recorded'), ('rejected', 'More information required')], default='draft', max_length=20)),
                ('staff_note', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('shop', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ondc_enrollment', to='shops.shop')),
            ],
        ),
    ]
