from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.html import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Order


@login_required
def order_invoice_pdf(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__seller_order__shop'),
        pk=order_id,
        user=request.user,
    )
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f'Jaunpur Footwear order {order.pk}',
        author='Jaunpur Footwear',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReceiptTitle', parent=styles['Title'], alignment=TA_CENTER, textColor=colors.HexColor('#173a55')))
    styles.add(ParagraphStyle(name='Right', parent=styles['Normal'], alignment=TA_RIGHT))
    story = [
        Paragraph('Jaunpur Footwear', styles['ReceiptTitle']),
        Paragraph('Order receipt', styles['Heading2']),
        Paragraph(f'Order #{order.pk} · {order.created_at:%d %b %Y, %I:%M %p}', styles['Normal']),
        Spacer(1, 8 * mm),
        Paragraph(f'<b>Customer:</b> {escape(order.full_name)}', styles['Normal']),
        Paragraph(f'<b>Mobile:</b> {escape(order.mobile)}', styles['Normal']),
        Paragraph(f'<b>Delivery address:</b> {escape(order.address)}, {escape(order.delivery_pincode)}', styles['Normal']),
        Paragraph(f'<b>Payment:</b> {escape(order.payment_method)} · {escape(order.get_payment_status_display())}', styles['Normal']),
        Spacer(1, 7 * mm),
    ]
    rows = [["Item / seller", "Size / color", "Qty", "Unit price", "Line total"]]
    subtotal = 0
    for item in order.items.all():
        line_total = item.price * item.quantity
        subtotal += line_total
        seller = item.seller_order.shop.name if item.seller_order_id and item.seller_order.shop_id else 'Jaunpur Footwear'
        rows.append([
            Paragraph(f'{escape(item.product_name)}<br/><font size="8">{escape(seller)}</font>', styles['BodyText']),
            f'{item.size} / {item.color or "—"}',
            str(item.quantity),
            f'INR {item.price:.2f}',
            f'INR {line_total:.2f}',
        ])
    table = Table(rows, colWidths=[64 * mm, 33 * mm, 13 * mm, 31 * mm, 33 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#173a55')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5df')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f7fa')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.extend([table, Spacer(1, 7 * mm)])
    totals = [
        ["Items subtotal", f'INR {subtotal:.2f}'],
        ["Discount", f'- INR {order.discount_amount:.2f}'],
        ["Delivery", f'INR {order.shipping_amount:.2f}'],
        ["Order total", f'INR {order.total_amount:.2f}'],
    ]
    totals_table = Table(totals, colWidths=[130 * mm, 44 * mm], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, 3), (-1, 3), 1, colors.HexColor('#173a55')),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([totals_table, Spacer(1, 10 * mm), Paragraph('This document summarizes the order recorded by Jaunpur Footwear.', styles['Italic'])])
    document.build(story)
    response = HttpResponse(output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="jaunpur-order-receipt-{order.pk}.pdf"'
    return response
