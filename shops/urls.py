from django.urls import path

from . import views


urlpatterns = [
    path('language/<str:language>/', views.set_site_language, name='set_site_language'),
    path('apply/', views.apply_for_shop, name='shop_application'),
    path('seller/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/verification/request/', views.request_shop_verification, name='request_shop_verification'),
    path('seller/profile/', views.seller_shop_profile, name='seller_shop_profile'),
    path('seller/promotions/', views.manage_promotions, name='manage_promotions'),
    path('seller/promotions/<int:promotion_id>/close/', views.deactivate_promotion, name='deactivate_promotion'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/payouts/', views.seller_payout_ledger, name='seller_payout_ledger'),
    path('seller/orders/<int:seller_order_id>/status/', views.update_seller_order_status, name='update_seller_order_status'),
    path('seller/products/add/', views.seller_product_form, name='seller_add_product'),
    path('seller/products/import/', views.import_seller_catalog, name='import_seller_catalog'),
    path('seller/products/<int:product_id>/edit/', views.seller_product_form, name='seller_edit_product'),
    path('seller/products/<int:product_id>/delete/', views.seller_delete_product, name='seller_delete_product'),
    path('seller/products/<int:product_id>/variants/', views.seller_manage_variants, name='seller_manage_variants'),
    path('coverage/', views.manage_shop_coverage, name='manage_shop_coverage'),
    path('coverage/<int:coverage_id>/remove/', views.remove_shop_coverage, name='remove_shop_coverage'),
    path('seller/fulfillment-slots/', views.manage_fulfillment_slots, name='manage_fulfillment_slots'),
    path('seller/fulfillment-slots/<int:slot_id>/remove/', views.remove_fulfillment_slot, name='remove_fulfillment_slot'),
    path('seller/marketplaces/', views.marketplace_hub, name='marketplace_hub'),
    path('seller/marketplaces/catalog/', views.manage_marketplace_catalog, name='manage_marketplace_catalog'),
    path('seller/marketplaces/<slug:channel>/request/', views.request_marketplace_setup, name='request_marketplace_setup'),
    path('seller/marketplaces/<slug:channel>/catalog.csv', views.export_marketplace_feed, name='export_marketplace_feed'),
    path('seller/ondc/', views.ondc_setup, name='ondc_setup'),
    path('', views.shop_directory, name='shop_directory'),
    path('<slug:slug>/', views.shop_page, name='shop_page'),
]
