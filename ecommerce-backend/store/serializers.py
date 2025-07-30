from rest_framework import serializers
from .models import (
    Category, Product, ProductImage, ProductVariant,
    Cart, CartItem, Order, OrderItem, Payment,
    OrderShippingAddress, ShippingAddress, Review
)
from django.contrib.auth import get_user_model

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SlugRelatedField(
        slug_field='slug',
        queryset=Category.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['slug', 'created_at', 'updated_at']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'is_featured', 'uploaded_at', 'updated_at', 'alt_text']
        read_only_fields = ['uploaded_at', 'updated_at']
        extra_kwargs = {
            'product': {'write_only': True}
        }


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'product', 'sku', 'size', 'color', 'price', 'stock', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'product': {'write_only': True}
        }


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True, source='category'
    )

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'description', 'brand', 'is_available',
            'category', 'category_id', 'images', 'variants',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']


class CartItemSerializer(serializers.ModelSerializer):
    product_variant_details = ProductVariantSerializer(source='product_variant', read_only=True)
    product_variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all(), write_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id', 'cart', 'product_variant', 'product_variant_details',
            'quantity', 'price_at_addition', 'created_at', 'updated_at'
        ]
        read_only_fields = ['price_at_addition', 'created_at', 'updated_at']
        extra_kwargs = {
            'cart': {'write_only': True}
        }

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'created_at', 'updated_at', 'checked_out']
        read_only_fields = ['created_at', 'updated_at', 'checked_out']

class OrderShippingAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderShippingAddress
        fields = [
            'id', 'order', 'full_name', 'address_line_1', 'address_line_2',
            'apartment', 'city', 'state', 'postal_code', 'country',
            'phone_number', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemSerializer(serializers.ModelSerializer):
    product_variant_details = ProductVariantSerializer(source='product_variant', read_only=True)
    product_variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all(), write_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'product_variant', 'product_variant_details', 'quantity',
            'unit_price_at_purchase', 'total_price_at_purchase',
            'product_name_snapshot', 'variant_details_snapshot',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'unit_price_at_purchase', 'total_price_at_purchase',
            'product_name_snapshot', 'variant_details_snapshot',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True) # Nested serializer for order items
    shipping_address = OrderShippingAddressSerializer(read_only=True) # Nested serializer for shipping address
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault()
    )
    cart = serializers.PrimaryKeyRelatedField(queryset=Cart.objects.all(), write_only=True)


    class Meta:
        model = Order
        fields = [
            'id', 'user', 'order_number', 'cart', 'status', 'total_price',
            'created_at', 'updated_at', 'items', 'shipping_address'
        ]
        read_only_fields = ['order_number', 'status', 'total_price', 'created_at', 'updated_at']


class PaymentSerializer(serializers.ModelSerializer):
    PAYMENT_METHOD_CHOICES = (
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
    )
    payment_method = serializers.ChoiceField(choices=PAYMENT_METHOD_CHOICES)

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'payment_method', 'amount', 'payment_status',
            'currency', 'transaction_id', 'payment_gateway_response',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'payment_status', 'transaction_id', 'payment_gateway_response']
        extra_kwargs = {
            'order': {'write_only': True}
        }


class ShippingAddressSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'user', 'full_name', 'address_line_1', 'address_line_2',
            'city', 'state', 'postal_code', 'country', 'phone_number',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault()
    )
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    
    #For reading, to display product title instead of just ID
    product_title = serializers.CharField(source='product.title', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'product', 'product_title', 'rating', 'title', 'comment',
            'is_approved', 'verified_purchase', 'created_at', 'updated_at'
        ]
        read_only_fields = ['is_approved', 'verified_purchase', 'created_at', 'updated_at']