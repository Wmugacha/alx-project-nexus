import os
import django
import random
from faker import Faker
from django.utils.text import slugify
from django.db import transaction
import django.db.utils

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce_project.settings")
django.setup()

from django.contrib.auth import get_user_model
from store.models import Category, Product, ProductVariant, ShippingAddress, Review

User = get_user_model()
fake = Faker('en_US')

def clear_data():
    ProductVariant.objects.all().delete()
    Product.objects.all().delete()
    ShippingAddress.objects.all().delete()
    Category.objects.all().delete()
    Review.objects.all().delete()
    User.objects.all().delete()
    print("🗑️ Cleared existing data")

def create_users(n=50):
    users = []
    for _ in range(n):
        email = fake.unique.email()
        username = email.split('@')[0][:30]  # Truncate to avoid username length issues
        try:
            user = User.objects.create_user(
                email=email,
                #username=username,
                password="testpassword123",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
            )
            users.append(user)
            print(f"👤 Created user: {email}")
        except django.db.utils.IntegrityError as e:
            print(f"Failed to create user with email {email}: {e}")
            continue
    return users

def create_shipping_addresses(users):
    for user in users:
        postal_code = fake.postcode()[:20]
        print(f"Creating ShippingAddress for {user.email} with postal_code: {postal_code}")
        try:
            ShippingAddress.objects.create(
                user=user,
                full_name=f"{fake.first_name()} {fake.last_name()}",
                address_line_1=fake.street_address(),
                address_line_2=fake.secondary_address() if random.choice([True, False]) else None,
                city=fake.city(),
                state=fake.state_abbr() if fake.country_code() == 'US' else None,
                postal_code=postal_code,
                country=fake.country_code(),
                phone_number=fake.phone_number()[:20] if random.choice([True, False]) else None,
                is_default=random.choice([True, False])
            )
            print(f"📦 Created shipping address for {user.email}")
        except django.db.utils.IntegrityError as e:
            print(f"Failed to create shipping address for {user.email}: {e}")
            continue

def create_categories():
    category_names = ['Clothing', 'Electronics', 'Books', 'Toys', 'Home']
    categories = []
    for name in category_names:
        try:
            category, _ = Category.objects.get_or_create(name=name)
            categories.append(category)
            print(f"🏷️ Created category: {name}")
        except django.db.utils.IntegrityError as e:
            print(f"Failed to create category {name}: {e}")
            continue
    return categories

def create_products(categories, n=15):
    products = []
    existing_slugs = set(Product.objects.values_list('slug', flat=True))
    for _ in range(n):
        base_name = fake.unique.word().capitalize()
        title = base_name
        slug = slugify(title)
        counter = 1
        while slug in existing_slugs:
            title = f"{base_name}-{counter}"
            slug = slugify(title)
            counter += 1
        description = fake.sentence()
        category = random.choice(categories)
        try:
            product = Product.objects.create(
                title=title,
                description=description,
                category=category
            )
            existing_slugs.add(slug)
            products.append(product)
            print(f"📦 Created product: {title} with slug: {slug} in category {category.name}")
        except django.db.utils.IntegrityError as e:
            print(f"Failed to create product {title}: {e}")
            continue
    return products

def create_variants(products, n=3):
    sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
    colors = ['Red', 'Blue', 'Green', 'Black', 'White', 'Yellow', 'Gray']
    existing_skus = set(ProductVariant.objects.values_list('sku', flat=True))
    for product in products:
        all_combinations = [(s, c) for s in sizes for c in colors]
        used_combinations = set(
            ProductVariant.objects.filter(product=product).values_list('size', 'color')
        )
        available_combinations = [combo for combo in all_combinations if combo not in used_combinations]
        random.shuffle(available_combinations)
        variants_created = 0
        for size, color in available_combinations[:min(n, len(available_combinations))]:
            base_sku = f"{product.slug}-{size}-{color}".lower()
            sku = base_sku
            counter = 1
            while sku in existing_skus:
                sku = f"{base_sku}-{counter}"
                counter += 1
            try:
                variant = ProductVariant.objects.create(
                    product=product,
                    size=size,
                    color=color,
                    price=round(random.uniform(10.0, 1000.0), 2),
                    stock=random.randint(1, 50),
                    sku=sku
                )
                existing_skus.add(sku)
                variants_created += 1
                print(f"🧩 Created variant for {product.title} - Size: {size}, Color: {color}, SKU: {sku}")
            except django.db.utils.IntegrityError as e:
                print(f"Failed to create variant for {product.title} - Size: {size}, Color: {color}: {e}")
                continue
        if variants_created < n:
            print(f"⚠️ Could only create {variants_created} variants for {product.title} due to unique constraints")

def create_reviews(products, users):
    for product in products:
        used_combinations = set(
            Review.objects.filter(product=product).values_list('user_id', flat=True)
        )
        num_reviews = random.randint(1, 3)
        available_users = [u for u in users if u.id not in used_combinations]
        for _ in range(min(num_reviews, len(available_users))):
            user = random.choice(available_users)
            try:
                Review.objects.create(
                    product=product,
                    user=user,
                    rating=random.randint(1, 5),
                    comment=fake.sentence(),
                )
                available_users.remove(user)
                print(f"⭐ Added review for {product.title} by {user.email}")
            except django.db.utils.IntegrityError as e:
                print(f"Failed to create review for {product.title} by {user.email}: {e}")
                continue
        if len(available_users) < num_reviews:
            print(f"⚠️ Could only create {num_reviews - len(available_users)} reviews for {product.title} due to unique constraints")

if __name__ == "__main__":
    print("🌱 Seeding database...")
    with transaction.atomic():
        clear_data()
        users = create_users(50)
        create_shipping_addresses(users)
        categories = create_categories()
        products = create_products(categories, 15)
        create_variants(products, 4)
        create_reviews(products, users)
    print("✅ Done seeding!")