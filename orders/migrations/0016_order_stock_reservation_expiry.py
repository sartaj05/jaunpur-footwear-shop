from datetime import timedelta

from django.db import migrations, models


def backfill_pending_payment_deadlines(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    pending_orders = Order.objects.filter(
        payment_method="Razorpay",
        payment_status="pending",
        status="pending",
        stock_released=False,
        stock_reservation_expires_at__isnull=True,
    ).only("pk", "created_at")

    batch = []
    for order in pending_orders.iterator(chunk_size=1000):
        order.stock_reservation_expires_at = order.created_at + timedelta(minutes=15)
        batch.append(order)
        if len(batch) == 500:
            Order.objects.bulk_update(batch, ["stock_reservation_expires_at"], batch_size=500)
            batch.clear()
    if batch:
        Order.objects.bulk_update(batch, ["stock_reservation_expires_at"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [("orders", "0015_return_refund_attempt")]

    operations = [
        migrations.AddField(
            model_name="order",
            name="stock_reservation_expires_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(backfill_pending_payment_deadlines, migrations.RunPython.noop),
    ]
