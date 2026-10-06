from django.urls import path

from . import views


urlpatterns = [
    path('apply/', views.apply_for_shop, name='shop_application'),
    path('coverage/', views.manage_shop_coverage, name='manage_shop_coverage'),
    path('coverage/<int:coverage_id>/remove/', views.remove_shop_coverage, name='remove_shop_coverage'),
    path('', views.shop_directory, name='shop_directory'),
    path('<slug:slug>/', views.shop_page, name='shop_page'),
]
