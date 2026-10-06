from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('orders', '0015_return_refund_attempt'),
    ]
    operations = [
        migrations.CreateModel(
            name='SupportTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=140)),
                ('category', models.CharField(choices=[('order', 'Order'), ('delivery', 'Delivery'), ('payment', 'Payment'), ('return', 'Return or exchange'), ('shop', 'Jaunpur shop'), ('other', 'Other')], default='other', max_length=12)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('under_review', 'Under review'), ('awaiting_customer', 'Waiting for customer'), ('resolved', 'Resolved'), ('closed', 'Closed')], default='open', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_support_tickets', to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='support_tickets', to='orders.order')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-updated_at', '-id']},
        ),
        migrations.CreateModel(
            name='SupportMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='support_messages', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='support.supportticket')),
            ],
            options={'ordering': ['created_at', 'id']},
        ),
    ]
