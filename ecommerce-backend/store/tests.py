# ecommerce/tests/test_models_integration.py

from django.test import TestCase
from decimal import Decimal
from .models import Order, OrderItem, Product, ProductVariant, Category, Cart, Review
from django.contrib.auth import get_user_model
from django.db import transaction

class SignalIntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create test objects
        cls.category = Category.objects.create(name='Electronics')
        cls.product = Product.objects.create(category=cls.category, title='Laptop', description='...', is_available=True)
        cls.variant = ProductVariant.objects.create(product=cls.product, sku='LAPTOP001', size='15inch', color='Black', price=Decimal('1000.00'), stock=10)
        cls.variant2 = ProductVariant.objects.create(product=cls.product, sku='LAPTOP002', size='13inch', color='Silver', price=Decimal('800.00'), stock=5)
        
        User = get_user_model()
        cls.user = User.objects.create_user(email='test@example.com', password='password')
        cls.other_user = User.objects.create_user(email='other@example.com', password='password')
        cls.cart = Cart.objects.create(user=cls.user) 
        cls.other_cart = Cart.objects.create(user=cls.other_user)

    def test_order_total_and_stock_decrease_on_order_item_creation(self):
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('0.00'))
        initial_stock = self.variant.stock 

        # Create OrderItem: triggers total and stock update
        order_item = OrderItem.objects.create(
            order=order,
            product_variant=self.variant,
            quantity=2,
            unit_price_at_purchase=self.variant.price
        )

        order.refresh_from_db()
        self.variant.refresh_from_db()

        # Assertions
        self.assertEqual(order.total_price, Decimal('2000.00'))
        self.assertEqual(self.variant.stock, initial_stock - 2)

    def test_stock_increase_on_order_item_deletion(self):
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('0.00'))
        order_item = OrderItem.objects.create(
            order=order,
            product_variant=self.variant,
            quantity=3,
            unit_price_at_purchase=self.variant.price
        )
        self.variant.refresh_from_db()
        stock_after_creation = self.variant.stock

        # Delete OrderItem: triggers stock increase
        order_item.delete()

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, stock_after_creation + 3)

    def test_cart_checked_out_on_order_creation(self):
        # Cart initially not checked out
        self.assertFalse(self.cart.checked_out)

        # Create Order: triggers cart checkout
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('100.00'))

        self.cart.refresh_from_db()
        self.assertTrue(self.cart.checked_out)

    def test_review_verified_purchase_status_on_review_creation(self):
        # Scenario 1: User purchased product
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('100.00'), status='delivered')
        OrderItem.objects.create(
            order=order,
            product_variant=self.variant,
            quantity=1,
            unit_price_at_purchase=self.variant.price
        )
        # Create review: triggers verification
        review = Review.objects.create(user=self.user, product=self.product, rating=5, comment="Great product!")
        review.refresh_from_db()
        self.assertTrue(review.verified_purchase)

        # Scenario 2: User NOT purchased product
        review_by_other = Review.objects.create(user=self.other_user, product=self.product, rating=3, comment="Okay.")
        review_by_other.refresh_from_db()
        self.assertFalse(review_by_other.verified_purchase)

    # --- Additional Tests for Stock Management ---

    def test_stock_decrease_on_order_item_quantity_increase(self):
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('0.00'))
        order_item = OrderItem.objects.create(
            order=order,
            product_variant=self.variant,
            quantity=1,
            unit_price_at_purchase=self.variant.price
        )
        self.variant.refresh_from_db()
        initial_stock = self.variant.stock

        # Increase quantity: triggers stock decrease
        order_item.quantity = 3
        order_item.save()

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, initial_stock - 2)
        order.refresh_from_db()
        self.assertEqual(order.total_price, Decimal('3000.00'))

    def test_stock_increase_on_order_item_quantity_decrease(self):
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('0.00'))
        order_item = OrderItem.objects.create(
            order=order,
            product_variant=self.variant,
            quantity=5,
            unit_price_at_purchase=self.variant.price
        )
        self.variant.refresh_from_db()
        initial_stock = self.variant.stock

        # Decrease quantity: triggers stock increase
        order_item.quantity = 2
        order_item.save()

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, initial_stock + 3)
        order.refresh_from_db()
        self.assertEqual(order.total_price, Decimal('2000.00'))

    def test_stock_return_on_order_cancellation(self):
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('0.00'), status='processing')
        OrderItem.objects.create(order=order, product_variant=self.variant, quantity=2, unit_price_at_purchase=self.variant.price)
        OrderItem.objects.create(order=order, product_variant=self.variant2, quantity=1, unit_price_at_purchase=self.variant2.price)
        
        self.variant.refresh_from_db()
        self.variant2.refresh_from_db()
        initial_stock_variant1 = self.variant.stock
        initial_stock_variant2 = self.variant2.stock

        # Change order status to cancelled
        order.status = 'cancelled'
        order.save()

        self.variant.refresh_from_db()
        self.variant2.refresh_from_db()
        # Assert stock returned
        self.assertEqual(self.variant.stock, initial_stock_variant1 + 2)
        self.assertEqual(self.variant2.stock, initial_stock_variant2 + 1)

    def test_stock_not_double_returned_on_multiple_cancellations(self):
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('0.00'), status='processing')
        OrderItem.objects.create(order=order, product_variant=self.variant, quantity=1, unit_price_at_purchase=self.variant.price)
        
        self.variant.refresh_from_db()
        initial_stock_after_purchase = self.variant.stock

        order.status = 'cancelled'
        order.save() # First cancellation

        self.variant.refresh_from_db()
        stock_after_first_cancel = self.variant.stock
        
        # Save order again with same status: stock should NOT change
        order.status = 'cancelled'
        order.save()

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, stock_after_first_cancel)

    # --- Additional Test for Cart Status Update ---

    def test_cart_status_not_updated_on_order_update(self):
        # Create order: marks cart as checked_out
        order = Order.objects.create(user=self.user, cart=self.cart, total_price=Decimal('100.00'))
        self.cart.refresh_from_db()
        self.assertTrue(self.cart.checked_out)

        # Update order: cart status should NOT change
        order.status = 'shipped'
        order.save()

        self.cart.refresh_from_db()
        self.assertTrue(self.cart.checked_out)

    # --- Additional Tests for Review Verified Purchase Status ---

    def test_review_verified_purchase_status_after_purchase(self):
        # Review BEFORE purchase
        review = Review.objects.create(user=self.user, product=self.product, rating=4, comment="Looks good!")
        review.refresh_from_db()
        self.assertFalse(review.verified_purchase)

        # User purchases product, order delivered
        order = Order.objects.create(user=self.user, cart=self.other_cart, total_price=Decimal('1000.00'), status='delivered')
        OrderItem.objects.create(order=order, product_variant=self.variant, quantity=1, unit_price_at_purchase=self.variant.price)
        
        # Save review: triggers verification
        review.save() 
        review.refresh_from_db()
        self.assertTrue(review.verified_purchase)

    def test_review_verified_purchase_status_on_order_status_change(self):
        # Review with pending order
        order = Order.objects.create(user=self.user, cart=self.other_cart, total_price=Decimal('1000.00'), status='pending')
        OrderItem.objects.create(order=order, product_variant=self.variant, quantity=1, unit_price_at_purchase=self.variant.price)
        
        review = Review.objects.create(user=self.user, product=self.product, rating=4, comment="Excited to get it!")
        review.refresh_from_db()
        self.assertFalse(review.verified_purchase)

        # Order status changes to delivered
        order.status = 'delivered'
        order.save()

        # Save review: ensures signal re-runs
        review.save() 
        review.refresh_from_db()
        self.assertTrue(review.verified_purchase)
