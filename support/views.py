from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from orders.models import Order

from .models import SupportMessage, SupportTicket


@login_required
def support_list(request):
    tickets = SupportTicket.objects.filter(user=request.user).select_related('order').order_by('-updated_at')
    return render(request, 'support/ticket_list.html', {'tickets': tickets})


@login_required
def support_create(request):
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        category = request.POST.get('category', 'other')
        description = request.POST.get('description', '').strip()
        order_id = request.POST.get('order_id', '').strip()
        order = None
        if order_id:
            order = Order.objects.filter(pk=order_id, user=request.user).first()
        if not subject or len(subject) > 140 or not description or len(description) < 10:
            messages.error(request, 'Enter a subject and at least 10 characters describing the issue.')
        elif category not in dict(SupportTicket.CATEGORY_CHOICES):
            messages.error(request, 'Choose a valid support category.')
        elif order_id and not order:
            messages.error(request, 'Choose one of your own orders or leave the order field blank.')
        else:
            ticket = SupportTicket.objects.create(
                user=request.user,
                order=order,
                subject=subject,
                category=category,
                description=description,
            )
            messages.success(request, 'Your support request was created.')
            return redirect('support_detail', ticket_id=ticket.pk)
    return render(request, 'support/ticket_create.html', {
        'categories': SupportTicket.CATEGORY_CHOICES,
        'orders': Order.objects.filter(user=request.user).order_by('-created_at')[:30],
    })


@login_required
def support_detail(request, ticket_id):
    access = Q(user=request.user)
    if request.user.is_staff:
        access |= Q()
    ticket = get_object_or_404(
        SupportTicket.objects.filter(access, pk=ticket_id).select_related('user', 'order').prefetch_related('messages__author'),
    )
    if request.method == 'POST':
        body = request.POST.get('message', '').strip()
        if ticket.status == 'closed':
            messages.error(request, 'This ticket is closed. Open a new request if you still need help.')
        elif len(body) < 2:
            messages.error(request, 'Enter a message before sending.')
        else:
            SupportMessage.objects.create(ticket=ticket, author=request.user, body=body)
            if ticket.status == 'resolved' and request.user == ticket.user:
                ticket.status = 'open'
            ticket.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Your reply was added.')
            return redirect('support_detail', ticket_id=ticket.pk)
    return render(request, 'support/ticket_detail.html', {'ticket': ticket})
