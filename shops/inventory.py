from django.db import transaction
from django.db.models import Sum

from products.models import Product, ProductVariant

from .models import MarketplaceProductMapping


def marketplace_reserved_quantity(product_id, variant_id=None, exclude_mapping_id=None):
    mappings = MarketplaceProductMapping.objects.filter(product_id=product_id, variant_id=variant_id)
    if exclude_mapping_id:
        mappings = mappings.exclude(pk=exclude_mapping_id)
    return mappings.aggregate(total=Sum('allocated_quantity'))['total'] or 0


def local_available_stock(stock_owner):
    return max(0, stock_owner.stock - marketplace_reserved_quantity(
        stock_owner.product_id if isinstance(stock_owner, ProductVariant) else stock_owner.pk,
        stock_owner.pk if isinstance(stock_owner, ProductVariant) else None,
    ))


@transaction.atomic
def update_mapping_allocation(mapping, quantity):
    mapping = MarketplaceProductMapping.objects.select_for_update(of=('self',)).select_related('product', 'variant').get(pk=mapping.pk)
    if mapping.variant_id:
        stock_owner = ProductVariant.objects.select_for_update().get(pk=mapping.variant_id)
    else:
        stock_owner = Product.objects.select_for_update().get(pk=mapping.product_id)
    reserved_elsewhere = marketplace_reserved_quantity(
        mapping.product_id,
        mapping.variant_id,
        exclude_mapping_id=mapping.pk,
    )
    if quantity < 0 or (
        quantity > mapping.allocated_quantity
        and reserved_elsewhere + quantity > stock_owner.stock
    ):
        return False
    mapping.allocated_quantity = quantity
    mapping.save(update_fields=['allocated_quantity', 'updated_at'])
    return True
