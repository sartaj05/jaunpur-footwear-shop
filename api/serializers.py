from rest_framework import serializers

from orders.models import Order
from products.models import Product, ProductVariant
from shops.models import Shop


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "size", "color", "stock", "price_override"]


class ProductSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source="brand.name", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "name_hi", "seller_sku", "brand", "category", "shop_id",
            "gender", "description", "description_hi", "price", "discount_price",
            "stock", "available_sizes", "image", "variants",
        ]
        read_only_fields = fields


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = [
            "id", "name", "slug", "phone", "city", "district", "pincode",
            "description", "description_hi", "opening_hours", "logo", "banner",
            "verification_status",
        ]
        read_only_fields = fields


class OrderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "status", "payment_method", "payment_status", "total_amount", "created_at"]
        read_only_fields = fields
