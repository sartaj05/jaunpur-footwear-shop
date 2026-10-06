from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import date, timedelta
import re

from products.models import Product, ProductVariant, Brand, Category
from orders.models import DeliveryAssignment, DeliveryRider, DeliveryRun, Order, OrderItem, OrderTrackingEvent, PaymentAttempt, SellerOrder
from orders.tasks import send_order_status_update_task
from footwear.task_dispatch import dispatch_background_task
from orders.payments import release_order_inventory
from accounts.services import award_loyalty_for_order
from django.db import transaction
from django.http import HttpResponse
import csv
from decimal import Decimal


@staff_member_required
def superadmin_dashboard(request):
    context = {
        'total_products': Product.objects.count(),
        'total_brands': Brand.objects.count(),
        'total_categories': Category.objects.count(),
        'total_orders': Order.objects.count(),
        'total_customers': User.objects.filter(is_staff=False).count(),
        'low_stock_products': (
            Product.objects.filter(variants__isnull=True, stock__lte=F('low_stock_threshold')).distinct().count()
            + ProductVariant.objects.filter(is_active=True, stock__lte=F('low_stock_threshold')).count()
        ),
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:8],
    }
    return render(request, 'dashboard/superadmin_dashboard.html', context)


@staff_member_required
def dashboard_brands(request):
    brands = Brand.objects.all().order_by('name')
    return render(request, 'dashboard/brands.html', {'brands': brands})


@staff_member_required
def add_brand(request):
    if request.method == 'POST':
        Brand.objects.create(
            name=request.POST.get('name'),
            logo=request.FILES.get('logo')
        )
        return redirect('dashboard_brands')

    return render(request, 'dashboard/brand_form.html', {'brand': None})


@staff_member_required
def edit_brand(request, pk):
    brand = get_object_or_404(Brand, pk=pk)

    if request.method == 'POST':
        brand.name = request.POST.get('name')

        if request.FILES.get('logo'):
            brand.logo = request.FILES.get('logo')

        brand.save()
        return redirect('dashboard_brands')

    return render(request, 'dashboard/brand_form.html', {'brand': brand})


@staff_member_required
def delete_brand(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    brand.delete()
    return redirect('dashboard_brands')


@staff_member_required
def dashboard_categories(request):
    categories = Category.objects.all().order_by('name')
    return render(request, 'dashboard/categories.html', {'categories': categories})


@staff_member_required
def add_category(request):
    if request.method == 'POST':
        Category.objects.create(
            name=request.POST.get('name'),
            image=request.FILES.get('image')
        )
        return redirect('dashboard_categories')

    return render(request, 'dashboard/category_form.html', {'category': None})


@staff_member_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category.name = request.POST.get('name')

        if request.FILES.get('image'):
            category.image = request.FILES.get('image')

        category.save()
        return redirect('dashboard_categories')

    return render(request, 'dashboard/category_form.html', {'category': category})


@staff_member_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    return redirect('dashboard_categories')


@staff_member_required
def dashboard_products(request):
    products = Product.objects.select_related('brand', 'category').order_by('-created_at')
    return render(request, 'dashboard/products.html', {'products': products})


@staff_member_required
def add_product(request):
    brands = Brand.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST':
        Product.objects.create(
            name=request.POST.get('name'),
            brand_id=request.POST.get('brand'),
            category_id=request.POST.get('category'),
            gender=request.POST.get('gender'),
            description=request.POST.get('description'),
            price=request.POST.get('price'),
            discount_price=request.POST.get('discount_price') or None,
            stock=request.POST.get('stock'),
            available_sizes=request.POST.get('available_sizes'),
            image=request.FILES.get('image'),
            is_active=True if request.POST.get('is_active') else False,
            is_featured=True if request.POST.get('is_featured') else False,
        )
        return redirect('dashboard_products')

    return render(request, 'dashboard/product_form.html', {
        'brands': brands,
        'categories': categories,
        'product': None,
    })


@staff_member_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    brands = Brand.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.brand_id = request.POST.get('brand')
        product.category_id = request.POST.get('category')
        product.gender = request.POST.get('gender')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.discount_price = request.POST.get('discount_price') or None
        product.stock = request.POST.get('stock')
        product.available_sizes = request.POST.get('available_sizes')
        product.is_active = True if request.POST.get('is_active') else False
        product.is_featured = True if request.POST.get('is_featured') else False

        if request.FILES.get('image'):
            product.image = request.FILES.get('image')

        product.save()
        return redirect('dashboard_products')

    return render(request, 'dashboard/product_form.html', {
        'brands': brands,
        'categories': categories,
        'product': product,
    })


@staff_member_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect('dashboard_products')


@staff_member_required
def dashboard_orders(request):
    orders = Order.objects.select_related('user').order_by('-created_at')
    return render(request, 'dashboard/orders.html', {'orders': orders})


@staff_member_required
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = dict(Order.STATUS_CHOICES)
        if new_status == 'cancelled' and order.payment_status == 'paid':
            messages.error(request, 'Refund the captured payment before cancelling this paid order.')
            return redirect('dashboard_orders')
        if new_status in valid_statuses and new_status != order.status:
            if new_status == 'cancelled':
                release_order_inventory(order)
                PaymentAttempt.objects.filter(order=order, status='created').update(status='failed')
            order.status = new_status
            order.save(update_fields=['status'])
            if new_status == 'delivered':
                award_loyalty_for_order(order)
            OrderTrackingEvent.objects.create(
                order=order,
                status=new_status,
                note=request.POST.get('note', '').strip() or valid_statuses[new_status],
                created_by=request.user,
            )
            transaction.on_commit(lambda order_id=order.pk: dispatch_background_task(send_order_status_update_task, order_id))

    return redirect('dashboard_orders')


@staff_member_required
def dashboard_customers(request):
    customers = User.objects.filter(is_staff=False).order_by('-date_joined')
    return render(request, 'dashboard/customers.html', {'customers': customers})


@staff_member_required
def sales_reports(request):
    periods = {'7': 7, '30': 30, '90': 90, '365': 365}
    selected_period = request.GET.get('days', '30')
    if selected_period not in periods:
        selected_period = '30'
    start_date = timezone.now() - timedelta(days=periods[selected_period])
    orders = Order.objects.filter(created_at__gte=start_date).exclude(status='cancelled')

    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="jaunpur-sales-{selected_period}-days.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Created at', 'Status', 'Payment method', 'Payment status', 'Items total INR', 'Discount INR', 'Delivery INR', 'Order total INR'])
        export_orders = orders.annotate(
            items_total=Sum(ExpressionWrapper(F('items__price') * F('items__quantity'), output_field=DecimalField(max_digits=12, decimal_places=2)))
        ).order_by('created_at', 'id')
        for order in export_orders:
            writer.writerow([
                order.pk, order.created_at.isoformat(), order.status, order.payment_method,
                order.payment_status, order.items_total or Decimal('0.00'), order.discount_amount,
                order.shipping_amount, order.total_amount,
            ])
        return response

    summary = orders.aggregate(order_count=Count('id'), total_revenue=Sum('total_amount'))
    order_count = summary['order_count'] or 0
    total_revenue = summary['total_revenue'] or 0
    average_order_value = total_revenue / order_count if order_count else 0
    sales_by_day = orders.annotate(day=TruncDate('created_at')).values('day').annotate(
        order_count=Count('id'), revenue=Sum('total_amount')
    ).order_by('day')
    top_products = OrderItem.objects.filter(order__in=orders).values('product_name').annotate(
        units_sold=Sum('quantity'),
        revenue=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField(max_digits=12, decimal_places=2))),
    ).order_by('-units_sold')[:10]

    return render(request, 'dashboard/sales_reports.html', {
        'selected_period': selected_period,
        'order_count': order_count,
        'total_revenue': total_revenue,
        'average_order_value': average_order_value,
        'sales_by_day': sales_by_day,
        'top_products': top_products,
    })


@staff_member_required
def seller_payouts(request):
    eligible = SellerOrder.objects.filter(
        status='delivered',
        payout_status='pending',
        shop__isnull=False,
    ).exclude(
        order__status='cancelled',
    ).filter(Q(order__payment_status='paid') | Q(order__payment_method='Cash on Delivery'))
    if request.method == 'POST':
        reference = request.POST.get('payout_reference', '').strip()
        if not reference:
            messages.error(request, 'Enter the bank or UPI transfer reference before recording a payout.')
        else:
            with transaction.atomic():
                seller_order = get_object_or_404(
                    SellerOrder.objects.select_for_update().select_related('order'),
                    pk=request.POST.get('seller_order_id'),
                )
                payment_is_ready = (
                    seller_order.order.payment_status == 'paid'
                    or seller_order.order.payment_method == 'Cash on Delivery'
                )
                if seller_order.status != 'delivered' or seller_order.payout_status != 'pending' or not payment_is_ready:
                    messages.error(request, 'This shop order is not eligible for payout yet.')
                else:
                    seller_order.payout_status = 'paid'
                    seller_order.payout_reference = reference
                    seller_order.paid_out_at = timezone.now()
                    seller_order.save(update_fields=['payout_status', 'payout_reference', 'paid_out_at'])
                    messages.success(request, 'Payout marked as sent. Confirm the transfer in your bank or UPI account.')
        return redirect('seller_payouts')

    paid = SellerOrder.objects.filter(payout_status='paid').select_related('shop', 'order').order_by('-paid_out_at')[:100]
    return render(request, 'dashboard/payouts.html', {
        'eligible_orders': eligible.select_related('shop', 'order').order_by('created_at'),
        'paid_orders': paid,
        'eligible_total': eligible.aggregate(total=Sum('net_amount'))['total'] or 0,
    })


@staff_member_required
def delivery_dispatch(request):
    pending_dispatch = SellerOrder.objects.filter(
        shop__isnull=False,
        fulfillment_method='delivery',
        delivery_assignment__isnull=True,
    ).exclude(status='delivered').exclude(order__status='cancelled').filter(
        Q(order__payment_status='paid') | Q(order__payment_method='Cash on Delivery')
    ).select_related('order', 'shop').order_by('order__delivery_pincode', 'fulfillment_date', 'created_at')
    error = ''
    if request.method == 'POST':
        try:
            rider_id = int(request.POST.get('rider_id', ''))
            pincode = request.POST.get('pincode', '').strip()
            delivery_date = date.fromisoformat(request.POST.get('delivery_date', ''))
            seller_order_ids = [int(value) for value in request.POST.getlist('seller_orders')]
        except (TypeError, ValueError):
            rider_id, pincode, delivery_date, seller_order_ids = 0, '', None, []
            error = 'Choose a rider, delivery date, Jaunpur PIN code, and orders.'
        rider = DeliveryRider.objects.filter(pk=rider_id, is_active=True).first()
        selected_orders = list(pending_dispatch.filter(pk__in=seller_order_ids))
        if not error and (not rider or not re.fullmatch(r'[1-9][0-9]{5}', pincode) or not delivery_date or delivery_date < timezone.localdate() or not seller_order_ids or len(selected_orders) != len(set(seller_order_ids))):
            error = 'Choose a valid active rider and eligible delivery orders.'
        elif not error and any(row.order.delivery_pincode != pincode for row in selected_orders):
            error = 'A delivery run can contain orders for one PIN code only.'
        elif not error and any(row.fulfillment_date and row.fulfillment_date != delivery_date for row in selected_orders):
            error = 'Use each order’s scheduled local delivery date.'
        if not error:
            with transaction.atomic():
                run = DeliveryRun.objects.create(
                    rider=rider,
                    pincode=pincode,
                    delivery_date=delivery_date,
                    status='in_progress',
                    route_note=request.POST.get('route_note', '').strip()[:240],
                    created_by=request.user,
                )
                for sequence, seller_order in enumerate(selected_orders, start=1):
                    DeliveryAssignment.objects.create(run=run, seller_order=seller_order, sequence=sequence)
                    seller_order.status = 'out_for_delivery'
                    seller_order.save(update_fields=['status'])
                    seller_order.order.status = 'out_for_delivery'
                    seller_order.order.save(update_fields=['status'])
                    OrderTrackingEvent.objects.create(
                        order=seller_order.order,
                        status='out_for_delivery',
                        note=f'Jaunpur delivery run {run.pk} assigned to {rider}.',
                        created_by=request.user,
                    )
            messages.success(request, f'Created PIN-code delivery run #{run.pk} with {len(selected_orders)} stop(s).')
            return redirect('delivery_dispatch')
    grouped_orders = {}
    for seller_order in pending_dispatch:
        grouped_orders.setdefault(seller_order.order.delivery_pincode or 'No PIN', []).append(seller_order)
    return render(request, 'dashboard/delivery_dispatch.html', {
        'grouped_orders': grouped_orders,
        'riders': DeliveryRider.objects.filter(is_active=True).select_related('user'),
        'runs': DeliveryRun.objects.select_related('rider__user').prefetch_related('assignments__seller_order__order', 'assignments__seller_order__shop').order_by('-created_at')[:40],
        'today': timezone.localdate().isoformat(),
        'error': error,
    })
