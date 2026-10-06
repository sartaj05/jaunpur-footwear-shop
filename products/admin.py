from django.contrib import admin
from .models import Brand, Category, Product, ProductVariant


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
    ]

    list_filter = ['brand', 'category', 'gender', 'is_active', 'is_featured']
    search_fields = ['name', 'brand__name', 'category__name']
