from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shops', '0016_ondc_participant_onboarding_handoff')]

    operations = [
        migrations.AddField('shopcoverage', 'min_delivery_days', models.PositiveSmallIntegerField(default=1)),
        migrations.AddField('shopcoverage', 'max_delivery_days', models.PositiveSmallIntegerField(default=3)),
        migrations.AddConstraint(
            model_name='shopcoverage',
            constraint=models.CheckConstraint(condition=models.Q(('max_delivery_days__gte', models.F('min_delivery_days'))), name='shop_coverage_eta_range_valid'),
        ),
        migrations.AddConstraint(
            model_name='shopcoverage',
            constraint=models.CheckConstraint(condition=models.Q(('max_delivery_days__lte', 30)), name='shop_coverage_eta_max_30_days'),
        ),
    ]
