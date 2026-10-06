from django.contrib import admin
from .models import Brand, Category, Product, ProductReview, ProductVariant, WishlistItem


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductVariantInline]
    list_display = [
        'id',
        'name',
        'brand',
        'category',
        'gender',
        'price',
        'discount_price',
        'stock',
        'is_active',
        'is_featured',
        'shop',
    ]

    list_filter = ['brand', 'category', 'gender', 'is_active', 'is_featured', 'shop']
    search_fields = ['name', 'brand__name', 'category__name']


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'product__name']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'title', 'body']
