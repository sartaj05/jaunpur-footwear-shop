from django.urls import path
from . import views

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('coupons/apply/', views.apply_coupon, name='apply_coupon'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('returns/<int:order_id>/', views.request_return, name='request_return'),
]
