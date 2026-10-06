from django.urls import path
from . import views

urlpatterns = [
    path('', views.superadmin_dashboard, name='superadmin_dashboard'),

    path('brands/', views.dashboard_brands, name='dashboard_brands'),
    path('brands/add/', views.add_brand, name='add_brand'),
    path('brands/edit/<int:pk>/', views.edit_brand, name='edit_brand'),
    path('brands/delete/<int:pk>/', views.delete_brand, name='delete_brand'),

    path('categories/', views.dashboard_categories, name='dashboard_categories'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),

    path('products/', views.dashboard_products, name='dashboard_products'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('products/delete/<int:pk>/', views.delete_product, name='delete_product'),

    path('orders/', views.dashboard_orders, name='dashboard_orders'),
    path('orders/update/<int:pk>/', views.update_order_status, name='update_order_status'),

    path('customers/', views.dashboard_customers, name='dashboard_customers'),
    path('reports/sales/', views.sales_reports, name='sales_reports'),
    path('payouts/', views.seller_payouts, name='seller_payouts'),
]
