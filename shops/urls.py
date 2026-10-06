from django.urls import path

from . import views


urlpatterns = [
    path('apply/', views.apply_for_shop, name='shop_application'),
    path('', views.shop_directory, name='shop_directory'),
    path('<slug:slug>/', views.shop_page, name='shop_page'),
]
