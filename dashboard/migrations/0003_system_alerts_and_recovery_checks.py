from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0002_background_job_run'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RecoveryCheck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('check_type', models.CharField(choices=[('database_restore', 'Database restore drill'), ('media_restore', 'Media restore drill'), ('payment_reconciliation', 'Payment reconciliation')], max_length=32)),
                ('status', models.CharField(choices=[('passed', 'Passed'), ('failed', 'Failed')], max_length=10)),
                ('details', models.TextField(max_length=2000)),
                ('checked_at', models.DateTimeField(auto_now_add=True)),
                ('checked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recovery_checks', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-checked_at', '-id']},
        ),
        migrations.CreateModel(
            name='SystemAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dedupe_key', models.CharField(max_length=220, unique=True)),
                ('source', models.CharField(max_length=24)),
                ('severity', models.CharField(choices=[('warning', 'Warning'), ('critical', 'Critical')], default='warning', max_length=10)),
                ('title', models.CharField(max_length=200)),
                ('details', models.TextField(blank=True)),
                ('state', models.CharField(choices=[('open', 'Open'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved')], default='open', max_length=14)),
                ('first_seen_at', models.DateTimeField(auto_now_add=True)),
                ('last_seen_at', models.DateTimeField(auto_now=True)),
                ('acknowledged_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('resolution_note', models.TextField(blank=True)),
                ('acknowledged_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='acknowledged_system_alerts', to=settings.AUTH_USER_MODEL)),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_system_alerts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['state', '-last_seen_at', '-id']},
        ),
    ]
