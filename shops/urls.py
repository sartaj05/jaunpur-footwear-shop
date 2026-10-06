from django.urls import path

from . import views


urlpatterns = [
    path('apply/', views.apply_for_shop, name='shop_application'),
    path('seller/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/orders/<int:seller_order_id>/status/', views.update_seller_order_status, name='update_seller_order_status'),
    path('seller/products/add/', views.seller_product_form, name='seller_add_product'),
    path('seller/products/<int:product_id>/edit/', views.seller_product_form, name='seller_edit_product'),
    path('seller/products/<int:product_id>/delete/', views.seller_delete_product, name='seller_delete_product'),
    path('seller/products/<int:product_id>/variants/', views.seller_manage_variants, name='seller_manage_variants'),
    path('coverage/', views.manage_shop_coverage, name='manage_shop_coverage'),
    path('coverage/<int:coverage_id>/remove/', views.remove_shop_coverage, name='remove_shop_coverage'),
    path('', views.shop_directory, name='shop_directory'),
    path('<slug:slug>/', views.shop_page, name='shop_page'),
]
