from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import OrderItem, Cart, ProductVariant, Review, Order, Cart
from django.db import transaction

# --- Order Total Calculation ---
@receiver(post_save, sender=OrderItem)
@receiver(post_delete, sender=OrderItem)
def update_order_total(sender, instance, **kwargs):
    order = instance.order
    # Flag to prevent recursion if saving the order triggers OrderItem signals
    if not hasattr(order, '_updating_total'):
        order._updating_total = True
        with transaction.atomic():
            total_price = sum(item.unit_price_at_purchase * item.quantity for item in order.items.all())
            order.total_price = total_price
            order.save()
        del order._updating_total # Clear flag

# --- Stock Management (OrderItem) ---

# Pre-save: Stores the old quantity of an OrderItem before it's saved.
@receiver(pre_save, sender=OrderItem)
def pre_save_order_item_stock_tracker(sender, instance, **kwargs):
    if instance.pk: # Only for existing instances (updates)
        try:
            old_instance = OrderItem.objects.get(pk=instance.pk)
            instance._old_quantity = old_instance.quantity
        except OrderItem.DoesNotExist:
            instance._old_quantity = 0 # Should not happen for existing, but safeguard
    else: # For new instances
        instance._old_quantity = 0

# Post-save: Adjusts stock based on OrderItem creation or quantity change.
@receiver(post_save, sender=OrderItem)
def handle_order_item_save(sender, instance, created, **kwargs):
    with transaction.atomic():
        product_variant = instance.product_variant
        if product_variant:
            if created:
                stock_change = instance.quantity
            else:
                old_quantity = getattr(instance, '_old_quantity', 0)
                stock_change = instance.quantity - old_quantity # Positive if quantity increased, negative if decreased

            product_variant.stock -= stock_change # Subtracting a negative number increases stock

            product_variant.stock = max(0, product_variant.stock) # Prevent negative stock
            product_variant.save()

# Post-delete: Returns stock when an OrderItem is deleted.
@receiver(post_delete, sender=OrderItem)
def handle_order_item_delete(sender, instance, **kwargs):
    with transaction.atomic():
        product_variant = instance.product_variant
        if product_variant:
            product_variant.stock += instance.quantity
            product_variant.save()

# --- Order Status Change (Stock Return) and Cart Status Update ---

# Pre-save: Store old status of an Order
@receiver(pre_save, sender=Order)
def pre_save_order_status_tracker(sender, instance, **kwargs):
    if instance.pk: # Only for existing instances (updates)
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_status = old_order.status
        except Order.DoesNotExist:
            instance._old_status = None # Should not happen for existing, but safeguard
    else: # For new instances
        instance._old_status = None

@receiver(post_save, sender=Order)
def handle_order_status_change_and_cart_update(sender, instance, created, **kwargs):
    # Flag to prevent re-entry from internal saves
    if hasattr(instance, '_order_signal_processed'):
        return
    instance._order_signal_processed = True

    old_status = getattr(instance, '_old_status', None) # Get old status from pre_save

    with transaction.atomic():
        # --- Stock Return Logic ---
        # Check if status changed TO cancelled/refunded AND was NOT already
        if (instance.status in ['cancelled', 'refunded'] and
            old_status not in ['cancelled', 'refunded']):
            
            for item in instance.items.all():
                product_variant = item.product_variant
                if product_variant:
                    product_variant.stock += item.quantity
                    product_variant.save()

        # --- Cart Status Update Logic ---
        # Only run if the order was just created
        if created:
            cart = instance.cart
            if cart and not cart.checked_out:
                # Flag for cart save to prevent recursion
                if not hasattr(cart, '_cart_status_updated'):
                    cart._cart_status_updated = True
                    cart.checked_out = True
                    cart.save()
                    del cart._cart_status_updated
    
    del instance._order_signal_processed # Clear flag

# --- Review Verified Purchase Status ---
@receiver(post_save, sender=Review)
def update_review_verified_purchase(sender, instance, created, **kwargs):
    # Flag to prevent re-entry from internal saves
    if hasattr(instance, '_review_verified_checked'):
        return
    instance._review_verified_checked = True

    with transaction.atomic():
        user = instance.user
        product = instance.product

        completed_order_statuses = ['delivered', 'shipped', 'paid']

        has_verified_purchase = Order.objects.filter(
            user=user,
            status__in=completed_order_statuses,
            items__product_variant__product=product
        ).exists()

        # Only save if the status actually changed
        if instance.verified_purchase != has_verified_purchase:
            instance.verified_purchase = has_verified_purchase
            instance.save()
    
    del instance._review_verified_checked # Clear flag
