from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from orders.models import Order
from products.models import Product
from products.search import product_search_query
from shops.models import Shop

from .serializers import OrderSummarySerializer, ProductSerializer, ShopSerializer


class ProductListApi(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("brand", "category", "shop").prefetch_related("variants")
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(product_search_query(query))
        return queryset.order_by("name", "id")


class ShopListApi(generics.ListAPIView):
    serializer_class = ShopSerializer
    permission_classes = [AllowAny]
    queryset = Shop.objects.filter(status="approved").order_by("name", "id")


class MyOrdersApi(generics.ListAPIView):
    serializer_class = OrderSummarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-created_at", "-id")
