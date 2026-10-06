from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('dashboard', '0001_staff_action_audit')]

    operations = [
        migrations.CreateModel(
            name='BackgroundJobRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=200)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('succeeded', 'Succeeded'), ('failed', 'Failed')], default='pending', max_length=12)),
                ('retry_count', models.PositiveSmallIntegerField(default=0)),
                ('error_summary', models.CharField(blank=True, max_length=300)),
                ('queued_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ['-queued_at', '-id']},
        ),
    ]
