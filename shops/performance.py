from collections import defaultdict

from django.db.models import Avg, Count, Q
from django.utils import timezone

from orders.models import SellerOrder
from support.models import SupportTicket

from .models import ShopReview


def performance_for_shops(shops, since):
    """Build recent, sample-aware fulfillment and service metrics per shop."""
    shop_ids = [shop.pk for shop in shops]
    metrics = {
        shop_id: {
            'order_count': 0,
            'delivered_count': 0,
            'cancelled_count': 0,
            'cancellation_rate': 0.0,
            'on_time_count': 0,
            'on_time_sample_count': 0,
            'on_time_rate': None,
            'average_fulfillment_hours': None,
            'complaint_count': 0,
            'open_complaint_count': 0,
            'average_rating': None,
            'review_count': 0,
        }
        for shop_id in shop_ids
    }
    if not shop_ids:
        return metrics

    period_orders = SellerOrder.objects.filter(
        shop_id__in=shop_ids,
        created_at__gte=since,
    )
    for summary in period_orders.values('shop_id').annotate(
        total=Count('id'),
        cancelled=Count('id', filter=Q(order__status='cancelled')),
        delivered=Count('id', filter=Q(status='delivered')),
    ):
        row = metrics[summary['shop_id']]
        row['order_count'] = summary['total']
        row['cancelled_count'] = summary['cancelled']
        row['delivered_count'] = summary['delivered']

    fulfillment_hours = defaultdict(list)
    delivered_orders = period_orders.filter(status='delivered').select_related('delivery_assignment__run')
    for seller_order in delivered_orders:
        assignment = getattr(seller_order, 'delivery_assignment', None)
        delivered_at = seller_order.delivered_at or (assignment.delivered_at if assignment else None)
        if delivered_at:
            elapsed = delivered_at - seller_order.created_at
            fulfillment_hours[seller_order.shop_id].append(max(0.0, elapsed.total_seconds() / 3600))

        scheduled_date = seller_order.fulfillment_date
        if scheduled_date is None and assignment:
            scheduled_date = assignment.run.delivery_date
        if scheduled_date and delivered_at:
            row['on_time_sample_count'] += 1
            if timezone.localtime(delivered_at).date() <= scheduled_date:
                row['on_time_count'] += 1

    for shop_id, row in metrics.items():
        if row['order_count']:
            row['cancellation_rate'] = round(100 * row['cancelled_count'] / row['order_count'], 1)
        if row['on_time_sample_count']:
            row['on_time_rate'] = round(100 * row['on_time_count'] / row['on_time_sample_count'], 1)
        if fulfillment_hours[shop_id]:
            row['average_fulfillment_hours'] = round(sum(fulfillment_hours[shop_id]) / len(fulfillment_hours[shop_id]), 1)

    open_statuses = ['open', 'under_review', 'awaiting_customer']
    complaint_rows = SupportTicket.objects.filter(shop_id__in=shop_ids, created_at__gte=since).values('shop_id').annotate(
        total=Count('id'),
        open_count=Count('id', filter=Q(status__in=open_statuses)),
    )
    for complaint in complaint_rows:
        metrics[complaint['shop_id']]['complaint_count'] = complaint['total']
        metrics[complaint['shop_id']]['open_complaint_count'] = complaint['open_count']

    review_rows = ShopReview.objects.filter(
        shop_id__in=shop_ids,
        is_visible=True,
        created_at__gte=since,
    ).values('shop_id').annotate(average=Avg('rating'), total=Count('id'))
    for review in review_rows:
        metrics[review['shop_id']]['average_rating'] = review['average']
        metrics[review['shop_id']]['review_count'] = review['total']
    return metrics
