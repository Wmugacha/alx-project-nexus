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
from django.db import transaction
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
import stripe
import json

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
        Action to convert the user's active cart into an Order.
        Expects 'cart_id' and 'shipping_address_id' in the request data.
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

            # Create Order
            order = Order.objects.create(
                user=user,
                cart=cart,
                status='pending',
                total_price=Decimal('0.00') # Will be updated by signal
            )

            # Create OrderItems from CartItems and update stock
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

            # Create OrderShippingAddress snapshot
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

            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderItemViewSet(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrderItem.objects.none()
        return OrderItem.objects.filter(order__user=self.request.user)


class OrderShippingAddressViewSet(viewsets.ModelViewSet):
    serializer_class = OrderShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrderShippingAddress.objects.none()
        return OrderShippingAddress.objects.filter(order__user=self.request.user)


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Payment.objects.none()
        return Payment.objects.filter(order__user=self.request.user)


    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate_payment(self, request):
        """
        Initiates a payment by creating a Stripe PaymentIntent.
        Expects 'order_id' and 'payment_method' ('card') in request data.
        """
        user = request.user
        order_id = request.data.get('order_id')
        payment_method = request.data.get('payment_method', 'card')

        if not order_id:
            return Response(
                {"detail": "Order ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = get_object_or_404(Order, id=order_id, user=user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Order not found or does not belong to user."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent initiating payment for already paid/processed orders
        if order.status in ['paid', 'processing']:
             return Response(
                {"detail": "Order has already been paid or is being processed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure order has a total price
        if order.total_price <= 0:
            return Response(
                {"detail": "Order total must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Create a Payment record with 'requires_action' status initially
            # This payment record will be updated by webhooks
            payment = Payment.objects.create(
                order=order,
                amount=order.total_price, # Use the actual order total
                payment_method=payment_method,
                status='requires_action' # Initial status for PaymentIntent flow
            )

            try:
                # Create a Stripe PaymentIntent
                # amount needs to be in cents (or smallest currency unit)
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(order.total_price * 100),
                    currency="usd", # Or your desired currency
                    payment_method_types=[payment_method],
                    metadata={'order_id': str(order.id), 'payment_id': str(payment.id)}
                )

                # Update Payment record with PaymentIntent ID
                payment.stripe_payment_intent_id = payment_intent.id
                payment.save()

                return Response(
                    {
                        "detail": "Payment intent created successfully.",
                        "client_secret": payment_intent.client_secret,
                        "payment_id": payment.id, # Return your internal payment ID
                        "order_id": order.id
                    },
                    status=status.HTTP_200_OK
                )

            except stripe.error.StripeError as e:
                # Handle Stripe API errors
                payment.status = 'failed'
                payment.save()
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                # Handle other unexpected errors
                payment.status = 'failed'
                payment.save()
                return Response(
                    {"detail": "An unexpected error occurred during payment initiation."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        # 1. Verify Webhook Signature (CRITICAL SECURITY STEP)
        # This protects against fake webhook calls by verifying the payload with your secret
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        print(f"Webhook Error: Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Webhook Error: Invalid signature: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        # Catch any other unexpected errors during event construction
        print(f"Webhook Error: Unexpected error during event construction: {e}")
        return HttpResponse(status=400)

    # 2. Handle the event
    event_type = event['type']
    event_data = event['data']['object'] # The Stripe object related to the event

    print(f"Received Stripe event: {event_type}") # For debugging

    with transaction.atomic():
        if event_type == 'payment_intent.succeeded':
            # A payment was successfully captured
            payment_intent_id = event_data['id']
            try:
                payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                payment.status = 'succeeded'
                payment.save()

                order = payment.order
                order.status = 'paid' # Update order status to 'paid'
                order.save()
                print(f"PaymentIntent {payment_intent_id} succeeded. Order {order.id} status updated to 'paid'.")
            except Payment.DoesNotExist:
                print(f"Error: Payment record for PaymentIntent {payment_intent_id} not found.")
                # It's generally safe to return 200 even if not found, to prevent Stripe retrying
                return HttpResponse(status=200) 

        elif event_type == 'payment_intent.payment_failed':
            # A payment failed
            payment_intent_id = event_data['id']
            try:
                payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
                payment.status = 'failed'
                payment.save()

                order = payment.order
                order.status = 'payment_failed' # Update order status to 'payment_failed'
                order.save()
                print(f"PaymentIntent {payment_intent_id} failed. Order {order.id} status updated to 'payment_failed'.")
            except Payment.DoesNotExist:
                print(f"Error: Payment record for PaymentIntent {payment_intent_id} not found.")
                return HttpResponse(status=200)

        # Future: add more events to Handle refunds

    return HttpResponse(status=200)


class ShippingAddressViewSet(viewsets.ModelViewSet):
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ShippingAddress.objects.none()
        return ShippingAddress.objects.filter(user=self.request.user)


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
