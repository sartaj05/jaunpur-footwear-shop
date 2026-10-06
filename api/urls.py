from django.urls import path

from .views import MyOrdersApi, ProductListApi, ShopListApi

urlpatterns = [
    path("products/", ProductListApi.as_view(), name="api-products"),
    path("shops/", ShopListApi.as_view(), name="api-shops"),
    path("my/orders/", MyOrdersApi.as_view(), name="api-my-orders"),
]
