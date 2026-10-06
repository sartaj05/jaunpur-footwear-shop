from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shops', '0019_marketplace_settlement_imports'),
    ]

    operations = [
        migrations.AddField(
            model_name='ondcenrollment',
            name='participant_connection_status',
            field=models.CharField(choices=[('not_configured', 'Participant adapter not configured'), ('connected', 'Participant connection confirmed'), ('failed', 'Participant connection check failed')], default='not_configured', max_length=20),
        ),
        migrations.AddField(
            model_name='ondcenrollment',
            name='participant_connection_checked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ondcenrollment',
            name='participant_connection_note',
            field=models.CharField(blank=True, max_length=240),
        ),
    ]
