from decimal import Decimal

from django.db import transaction

from .models import LoyaltyAccount, LoyaltyTransaction


@transaction.atomic
def award_loyalty_for_order(order):
    points = int(Decimal(order.total_amount) // Decimal('100.00'))
    if points < 1:
        return 0

    account, _ = LoyaltyAccount.objects.get_or_create(user_id=order.user_id)
    account = LoyaltyAccount.objects.select_for_update().get(pk=account.pk)
    if LoyaltyTransaction.objects.filter(order=order, transaction_type='earned').exists():
        return 0

    LoyaltyTransaction.objects.create(
        account=account,
        order=order,
        transaction_type='earned',
        points=points,
        note=f'Order #{order.pk} delivered',
    )
    account.points += points
    account.save(update_fields=['points', 'updated_at'])
    return points
