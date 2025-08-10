from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from .pagination import ResultsSetPagination
from .permissions import IsAdminOrReadOnly, ReviewPermissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import stripe
import json

stripe.api_key = settings.STRIPE_SECRET_KEY


from .models import (
    Category, Product, ProductImage, ProductVariant,
    Cart, CartItem, Order, OrderItem, Payment,
    OrderShippingAddress, ShippingAddress, Review
)
from .serializers import (
    CategorySerializer, ProductSerializer, ProductImageSerializer, ProductVariantSerializer,
    CartSerializer, CartItemSerializer, OrderSerializer, OrderItemSerializer, PaymentSerializer,
    OrderShippingAddressSerializer, ShippingAddressSerializer, ReviewSerializer
)
from .filters import (
    CategoryFilter, ProductFilter, ProductVariantFilter,
    OrderFilter, ReviewFilter
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CategoryFilter


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['title', 'brand']
    filterset_class = ProductFilter
    pagination_class = ResultsSetPagination


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.all().order_by('-created_at')
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductVariantFilter
    ordering_fields = ['price', 'created_at']
    pagination_class = ResultsSetPagination


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Cart.objects.none()
        return Cart.objects.filter(user=self.request.user)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CartItem.objects.none()
        return CartItem.objects.filter(cart__user=self.request.user)


    def perform_create(self, serializer):
        user = self.request.user
        
        # Get or Create the user's active cart
        user_cart, created = Cart.objects.get_or_create(user=user, checked_out=False)

        # Get the product variant and its current price
        product_variant = serializer.validated_data.get('product_variant')
        if not product_variant:
            raise serializers.ValidationError("Product variant is required.")

        # Set price_at_addition from the current product variant price
        price_at_addition = product_variant.price

        # Check if the item already exists in the cart (for updating quantity instead of creating new)
        existing_cart_item = CartItem.objects.filter(
            cart=user_cart,
            product_variant=product_variant
        ).first()

        if existing_cart_item:
            # If item exists, update its quantity
            existing_cart_item.quantity += serializer.validated_data.get('quantity', 1)
            existing_cart_item.save()

            serializer.instance = existing_cart_item # Set instance for response
        else:
            # If item does not exist, create a new one
            serializer.save(
                cart=user_cart,
                price_at_addition=price_at_addition # Set the price
            )

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter
    pagination_class = ResultsSetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        Action to convert the user's active cart into an Order,
        create an associated Payment record, and initiate a Stripe Checkout Session.
        Expects 'cart_id' and 'shipping_address_id' in the request data.
        Returns the Stripe Checkout Session URL for client redirection.
        """
        user = request.user
        cart_id = request.data.get('cart_id')
        shipping_address_id = request.data.get('shipping_address_id')

        if not cart_id or not shipping_address_id:
            return Response(
                {"detail": "Both 'cart_id' and 'shipping_address_id' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Get the user's active cart
            cart = get_object_or_404(Cart, id=cart_id, user=user, checked_out=False)
            cart_items = cart.items.all()

            if not cart_items.exists():
                return Response(
                    {"detail": "Cannot checkout an empty cart."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2. Get the user's selected shipping address
            shipping_address = get_object_or_404(ShippingAddress, id=shipping_address_id, user=user)

        except (Cart.DoesNotExist, ShippingAddress.DoesNotExist) as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use a transaction to ensure atomicity of the checkout process
        with transaction.atomic():
            # Perform stock validation before creating order items
            for cart_item in cart_items:
                product_variant = cart_item.product_variant
                if product_variant.stock < cart_item.quantity:
                    return Response(
                        {"detail": f"Not enough stock for {product_variant}. Available: {product_variant.stock}, Requested: {cart_item.quantity}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 3. Create Order
            # Initial status is 'pending' before payment confirmation
            order = Order.objects.create(
                user=user,
                cart=cart,
                status='pending',
                total_price=Decimal('0.00') # Will be updated by signal (OrderItem post_save)
            )

            # 4. Create OrderItems from CartItems and prepare Stripe line_items
            line_items_for_stripe = []
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_variant=cart_item.product_variant,
                    quantity=cart_item.quantity,
                    unit_price_at_purchase=cart_item.product_variant.price, # Snapshot price
                    product_name_snapshot=cart_item.product_variant.product.title,
                    variant_details_snapshot=f"Size: {cart_item.product_variant.size}, Color: {cart_item.product_variant.color}"
                )
                # Stock reduction is handled by signals (OrderItem post_save)

                # Stripe expects unit_amount in cents/smallest currency unit
                # Ensure cart_item.product_variant.price is Decimal for accurate multiplication
                unit_amount_cents = int(cart_item.product_variant.price * 100)

                line_items_for_stripe.append({
                    'price_data': {
                        'currency': 'usd', # IMPORTANT: Use your actual currency (e.g., 'usd', 'eur', 'etb')
                        'product_data': {
                            'name': cart_item.product_variant.product.title,
                            'description': f"SKU: {cart_item.product_variant.sku}, Size: {cart_item.product_variant.size}, Color: {cart_item.product_variant.color}",
                            # 'images': [cart_item.product_variant.product.image.url] # Add if you have product images
                        },
                        'unit_amount': unit_amount_cents,
                    },
                    'quantity': cart_item.quantity,
                })

            # 5. Create OrderShippingAddress snapshot
            OrderShippingAddress.objects.create(
                order=order,
                full_name=shipping_address.full_name,
                address_line_1=shipping_address.address_line_1,
                address_line_2=shipping_address.address_line_2,
                apartment=getattr(shipping_address, 'apartment', None),
                city=shipping_address.city,
                state=shipping_address.state,
                postal_code=shipping_address.postal_code,
                country=shipping_address.country,
                phone_number=shipping_address.phone_number
            )
            # Cart checked_out status is handled by signals (Order post_save)

            # Reload order to get updated total_price from signal
            order.refresh_from_db()

            # 6. Create a Payment record *before* initiating Stripe session
            # This payment record will be updated by webhooks
            payment = Payment.objects.create(
                order=order,
                amount=order.total_price, # Use the actual order total
                payment_method='stripe_checkout', # Indicate method used
                status='requires_action' # Initial status for the payment flow
            )

            print(f"DEBUG: Preparing Stripe Checkout Session for Order ID: {order.id}, Payment ID: {payment.id}")
            print(f"DEBUG: Line Items being sent to Stripe: {line_items_for_stripe}")
            print(f"DEBUG: Metadata being sent to Stripe: {{'order_id': str(order.id), 'user_id': str(user.id), 'cart_id': str(cart.id), 'payment_id': str(payment.id)}}")
            try:
                # 7. Create Stripe Checkout Session
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'], # Or include other types you've enabled in Stripe Dashboard
                    line_items=line_items_for_stripe,
                    mode='payment',
                    # Crucial URLs for redirection after payment
                    success_url=f"{settings.FRONTEND_URL}/order-success?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=f"{settings.FRONTEND_URL}/cart",
                    customer_email=user.email, # Pre-fill customer email on Stripe page
                    metadata={ # Pass your internal IDs for webhook reconciliation
                        'order_id': str(order.id),
                        'user_id': str(user.id),
                        'cart_id': str(cart.id),
                        'payment_id': str(payment.id), # Pass internal payment ID for webhook
                    },
                )

                # 8. Update the order and payment with the Checkout Session ID
                order.stripe_checkout_session_id = checkout_session.id
                order.save()

                payment.stripe_session_id = checkout_session.id # Link payment to Stripe Session
                payment.save()

                return Response(
                    {
                        "checkout_url": checkout_session.url, # URL to redirect frontend
                        "order_id": order.id,
                        "session_id": checkout_session.id,
                        "payment_id": payment.id # Return your internal payment ID
                    },
                    status=status.HTTP_200_OK
                )

            except stripe.error.StripeError as e:
                # If Stripe API call fails, mark order/payment as failed
                order.status = 'payment_failed'
                order.save()
                payment.status = 'failed'
                payment.save()
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                # Catch any other unexpected errors
                order.status = 'payment_failed'
                order.save()
                payment.status = 'failed'
                payment.save()
                print(f"Checkout error: {e}") # Log for debugging
                return Response(
                    {"detail": "An unexpected error occurred during checkout."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrderItem.objects.none()
        return OrderItem.objects.filter(order__user=self.request.user)

class PaymentViewSet(viewsets.ModelViewSet):
    """
    A viewset for retrieving Payment records.
    The creation of Payment records is now handled by OrderViewSet.checkout,
    and their status updates are handled by the Stripe webhook.
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Payment.objects.none()
        return Payment.objects.filter(order__user=self.request.user)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        # 1. Verify Webhook Signature (CRITICAL SECURITY STEP)
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        print(f"Webhook Error: Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print(f"Webhook Error: Invalid signature: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        print(f"Webhook Error: Unexpected error during event construction: {e}")
        return HttpResponse(status=400)

    # 2. Handle the event
    event_type = event['type']
    event_data = event['data']['object'] # The Stripe object related to the event

    print(f"Received Stripe event: {event_type}") # For debugging

    with transaction.atomic():
        if event_type == 'checkout.session.completed':
            # This is the primary event for order fulfillment when using Stripe Checkout Sessions.
            session_id = event_data['id']
            # Retrieve your internal order_id and payment_id from metadata
            order_id = event_data['metadata'].get('order_id')
            payment_id = event_data['metadata'].get('payment_id') # Get internal payment ID

            print(f"Stripe Checkout Session {session_id} completed. Internal Order ID: {order_id}, Payment ID: {payment_id}")

            try:
                # Retrieve the pre-created Payment record and update its status
                payment = Payment.objects.get(id=payment_id, order__id=order_id)
                payment.status = 'succeeded'
                payment.stripe_payment_intent_id = event_data['payment_intent'] # Link to PI created by CS
                payment.stripe_session_id = session_id # Ensure this is also saved if needed
                payment.save()

                # Update the associated Order status
                order = payment.order
                order.status = 'paid'
                order.stripe_checkout_session_id = session_id # Link order to Checkout Session
                order.save()
                
                # Optional: Mark cart as checked out if not already handled by a signal
                # order.cart.checked_out = True
                # order.cart.save()

                print(f"Order {order_id} status updated to 'paid' and Payment {payment_id} marked as succeeded.")
            except Payment.DoesNotExist:
                print(f"Error: Payment record with ID {payment_id} for Order {order_id} not found for Checkout Session {session_id}.")
                return HttpResponse(status=200) # Always return 200 OK to Stripe
            except Order.DoesNotExist: # Should ideally not happen if Payment exists and links to Order
                print(f"Error: Order with ID {order_id} not found during webhook processing for session {session_id}.")
                return HttpResponse(status=200)
            except Exception as e:
                print(f"Error processing checkout.session.completed for order {order_id}, payment {payment_id}: {e}")
                return HttpResponse(status=200)

        elif event_type == 'payment_intent.succeeded':
            # This handler is for direct PaymentIntent flows.(Earlier implementation)
            # This part handles PaymentIntents directly, outside of Checkout Sessions.
            payment_intent_id = event_data['id']
            try:
                payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                payment.status = 'succeeded'
                payment.save()

                order = payment.order
                order.status = 'paid'
                order.save()
                print(f"PaymentIntent {payment_intent_id} succeeded. Order {order.id} status updated to 'paid'.")
            except Payment.DoesNotExist:
                print(f"Error: Payment record for PaymentIntent {payment_intent_id} not found.")
                return HttpResponse(status=200) 

        elif event_type == 'payment_intent.payment_failed':
            # This handler is also for direct PaymentIntent flows.
            payment_intent_id = event_data['id']
            try:
                payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                payment.status = 'failed'
                payment.save()

                order = payment.order
                order.status = 'payment_failed'
                order.save()
                print(f"PaymentIntent {payment_intent_id} failed. Order {order.id} status updated to 'payment_failed'.")
            except Payment.DoesNotExist:
                print(f"Error: Payment record for PaymentIntent {payment_intent_id} not found.")
                return HttpResponse(status=200)

        # You can add more event handlers here for other Stripe events if needed
        # e.g., 'charge.refunded', 'invoice.paid', etc.

    return HttpResponse(status=200)


class ShippingAddressViewSet(viewsets.ModelViewSet):
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ShippingAddress.objects.none()
        return ShippingAddress.objects.filter(user=self.request.user)

class OrderShippingAddressViewSet(viewsets.ModelViewSet):
    serializer_class = OrderShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrderShippingAddress.objects.none()
        return OrderShippingAddress.objects.filter(order__user=self.request.user)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [ReviewPermissions]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ReviewFilter
    ordering_fields = ['rating', 'created_at']
    search_fields = ['product__title', 'comment']
    pagination_class = ResultsSetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Review.objects.none()
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        else:
            return queryset.filter(is_approved=True)

# These simple functions are for your frontend redirection after Stripe checkout
# They are not part of the DRF ViewSet. Ensure they are mapped in your urls.py.
def payment_success(request):
    # This view would typically load a frontend template showing success or redirect to a SPA route
    return HttpResponse("<h1>Payment Successful! 🎉 Your order is being processed.</h1>")

def payment_cancelled(request):
    # This view would typically load a frontend template showing cancellation or redirect to a SPA route
    return HttpResponse("<h1>Payment Cancelled 😔</h1><p>You can try again or check your cart.</p>")

