from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="StaffActionAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("route_name", models.CharField(blank=True, max_length=160)),
                ("method", models.CharField(max_length=8)),
                ("response_status", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="staff_action_audits", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
