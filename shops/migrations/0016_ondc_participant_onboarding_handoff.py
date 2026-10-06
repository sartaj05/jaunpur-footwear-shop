from django.db import migrations, models


def normalize_legacy_statuses(apps, schema_editor):
    enrollment = apps.get_model('shops', 'ONDCEnrollment')
    enrollment.objects.filter(status='onboarded').update(status='production_approval_pending')
    enrollment.objects.filter(status='rejected').update(status='needs_changes')


def restore_legacy_statuses(apps, schema_editor):
    enrollment = apps.get_model('shops', 'ONDCEnrollment')
    enrollment.objects.filter(status__in=['partner_confirmed', 'catalog_exported', 'production_approval_pending', 'live']).update(status='onboarded')
    enrollment.objects.filter(status='needs_changes').update(status='rejected')


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0015_marketplace_shared_stock_and_orders'),
    ]

    operations = [
        migrations.AddField(
            model_name='ondcenrollment',
            name='participant_seller_id',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='ondcenrollment',
            name='network_subscriber_id',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='ondcenrollment',
            name='participant_supports_retail',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='ondcenrollment',
            name='catalog_exported_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ondcenrollment',
            name='production_activated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ondcenrollment',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('submitted', 'Partner request submitted'),
                    ('partner_confirmed', 'Seller Network Participant confirmed'),
                    ('catalog_exported', 'Catalog handoff exported'),
                    ('production_approval_pending', 'Production approval pending'),
                    ('live', 'Production connection confirmed'),
                    ('needs_changes', 'More information required'),
                ],
                default='draft',
                max_length=32,
            ),
        ),
        migrations.RunPython(normalize_legacy_statuses, restore_legacy_statuses),
    ]
