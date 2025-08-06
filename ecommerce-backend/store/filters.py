import django_filters
from .models import Category, Product, ProductVariant, Order, Review

class CategoryFilter(django_filters.FilterSet):
    parent_slug = django_filters.CharFilter(field_name='parent__slug')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = Category
        fields = ['parent', 'is_active']


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__slug')
    brand = django_filters.CharFilter(lookup_expr='iexact')
    is_available = django_filters.BooleanFilter()

    class Meta:
        model = Product
        fields = ['category', 'brand', 'is_available']


class ProductVariantFilter(django_filters.FilterSet):
    product = django_filters.CharFilter(field_name='product__slug')
    size = django_filters.CharFilter(lookup_expr='iexact')
    color = django_filters.CharFilter(lookup_expr='iexact')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_stock = django_filters.NumberFilter(field_name='stock', lookup_expr='gte')
    max_stock = django_filters.NumberFilter(field_name='stock', lookup_expr='lte')

    class Meta:
        model = ProductVariant
        fields = ['product', 'size', 'color', 'min_price', 'max_price', 'min_stock', 'max_stock']

class OrderFilter(django_filters.FilterSet):
    user_email = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    status = django_filters.CharFilter(lookup_expr='iexact')
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Order
        fields = ['user_email', 'status', 'start_date', 'end_date']

class ReviewFilter(django_filters.FilterSet):
    product = django_filters.CharFilter(field_name='product__slug')
    user_email = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    rating = django_filters.NumberFilter()
    is_approved = django_filters.BooleanFilter()

    class Meta:
        model = Review
        fields = ['product', 'user_email', 'rating', 'is_approved']