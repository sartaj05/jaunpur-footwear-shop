from django.urls import path
from . import views
from .webhooks import razorpay_webhook
from .documents import order_invoice_pdf

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('coupons/apply/', views.apply_coupon, name='apply_coupon'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('cancel/<int:order_id>/', views.request_order_cancellation, name='request_order_cancellation'),
    path('invoice/<int:order_id>/', order_invoice_pdf, name='order_invoice'),
    path('rider/deliveries/', views.rider_deliveries, name='rider_deliveries'),
    path('returns/<int:order_id>/', views.request_return, name='request_return'),
    path('payments/razorpay/verify/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('payments/razorpay/fail/<int:attempt_id>/', views.fail_razorpay_payment, name='fail_razorpay_payment'),
    path('payments/razorpay/resume/<int:order_id>/', views.resume_razorpay_payment, name='resume_razorpay_payment'),
    path('payments/razorpay/webhook/', razorpay_webhook, name='razorpay_webhook'),
]
