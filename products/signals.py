from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import InventoryMovement, Product, ProductVariant


@receiver(pre_save, sender=Product)
@receiver(pre_save, sender=ProductVariant)
def remember_previous_stock(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_stock = sender.objects.filter(pk=instance.pk).values_list("stock", flat=True).first()
    else:
        instance._previous_stock = 0


@receiver(post_save, sender=Product)
@receiver(post_save, sender=ProductVariant)
def record_stock_change(sender, instance, created, **kwargs):
    delta = instance.stock - getattr(instance, "_previous_stock", 0)
    if not delta:
        return
    is_variant = isinstance(instance, ProductVariant)
    product = instance.product if is_variant else instance
    InventoryMovement.objects.create(
        product=product,
        variant=instance if is_variant else None,
        delta=delta,
        stock_after=instance.stock,
        reason=getattr(instance, "_stock_change_reason", "initial_stock" if created else "stock_update"),
        reference=getattr(instance, "_stock_change_reference", ""),
        actor=getattr(instance, "_stock_change_actor", None),
    )
