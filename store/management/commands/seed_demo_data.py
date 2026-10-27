from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from store.models import Brand, Category, Product, ProductReview


class Command(BaseCommand):
    help = "Create or update the ShopSphere demonstration catalog."

    def handle(self, *args, **options):
        categories = [
            "Electronics", "Fashion", "Home & Kitchen", "Beauty & Personal Care",
            "Sports & Fitness", "Books", "Toys & Games", "Grocery & Essentials",
        ]
        category_objects = {}
        for name in categories:
            category_objects[name] = Category.objects.update_or_create(
                slug=slugify(name), defaults={"name": name, "is_active": True}
            )[0]
        brand_names = ["Northstar", "Everyday Co.", "Urban Field", "Brightside", "Aster & Oak", "PageTurner"]
        brands = {
            name: Brand.objects.update_or_create(slug=slugify(name), defaults={"name": name})[0]
            for name in brand_names
        }
        reviewer, created = User.objects.get_or_create(
            username="shopsphere_demo_reviewer",
            defaults={
                "first_name": "ShopSphere",
                "last_name": "Sample reviewer",
                "is_active": False,
            },
        )
        if created:
            reviewer.set_unusable_password()
            reviewer.save(update_fields=["password"])
        catalog = [
            ("Aero 5G Smartphone", "Electronics", "Northstar", "A vivid 5G smartphone with a crisp display, reliable battery life and an intuitive camera.", "42999.00", "49999.00", 18, True),
            ("Studio Pro Laptop", "Electronics", "Northstar", "A lightweight everyday laptop with fast storage and a bright, colour-accurate screen.", "74990.00", "84990.00", 12, True),
            ("Cloud Wireless Headphones", "Electronics", "Brightside", "Comfortable wireless headphones with clear sound and all-day listening comfort.", "5999.00", "7999.00", 35, True),
            ("Everyday Smartwatch", "Electronics", "Brightside", "A versatile smartwatch for activity tracking, notifications and quick everyday tasks.", "8499.00", "10999.00", 22, False),
            ("Portable Bluetooth Speaker", "Electronics", "Urban Field", "A compact speaker built for room-filling audio at home or on the go.", "2499.00", "3299.00", 28, False),
            ("Mechanical Keyboard", "Electronics", "Northstar", "A tactile, full-size keyboard designed for productive work and comfortable typing.", "4299.00", "4999.00", 17, False),
            ("Classic Cotton Shirt", "Fashion", "Everyday Co.", "A breathable cotton shirt with a relaxed fit that works from weekdays to weekends.", "1499.00", "1999.00", 42, True),
            ("Canvas Everyday Sneakers", "Fashion", "Urban Field", "Easy-to-style canvas sneakers with a cushioned sole for daily walks.", "2199.00", "2799.00", 31, False),
            ("Lightweight Travel Backpack", "Fashion", "Urban Field", "A practical, lightweight backpack with organised compartments for daily essentials.", "1899.00", "2499.00", 26, False),
            ("Soft Knit Pullover", "Fashion", "Aster & Oak", "A soft, mid-weight knit layer made for comfortable all-season styling.", "2399.00", "2999.00", 19, False),
            ("Insulated Steel Bottle", "Home & Kitchen", "Everyday Co.", "A reusable insulated bottle designed to keep drinks at a comfortable temperature.", "899.00", "1199.00", 65, True),
            ("Ceramic Dinner Set", "Home & Kitchen", "Aster & Oak", "A clean-lined ceramic dinner set for relaxed family meals and entertaining.", "2799.00", "3499.00", 15, False),
            ("Compact Air Fryer", "Home & Kitchen", "Brightside", "A simple countertop air fryer with easy controls for quick weeknight cooking.", "4999.00", "6499.00", 9, True),
            ("Pour-Over Coffee Kit", "Home & Kitchen", "Aster & Oak", "A minimal pour-over coffee set for a consistent, unhurried morning brew.", "1599.00", "1999.00", 21, False),
            ("Daily Hydration Serum", "Beauty & Personal Care", "Brightside", "A lightweight, fragrance-free hydration serum for a simple daily skincare routine.", "699.00", "899.00", 38, True),
            ("Gentle Cleansing Set", "Beauty & Personal Care", "Everyday Co.", "A mild daily cleansing duo developed for a refreshing, uncomplicated routine.", "549.00", "699.00", 44, False),
            ("Mineral Sunscreen SPF 50", "Beauty & Personal Care", "Brightside", "A broad-spectrum mineral sunscreen with a comfortable, everyday finish.", "799.00", "999.00", 32, False),
            ("Daily Wellness Kit", "Beauty & Personal Care", "Aster & Oak", "A considered set of everyday personal-care essentials for travel or home.", "999.00", "1299.00", 20, False),
            ("Adjustable Yoga Mat", "Sports & Fitness", "Urban Field", "A supportive, grippy yoga mat with a comfortable surface for daily movement.", "1299.00", "1699.00", 27, True),
            ("Resistance Band Set", "Sports & Fitness", "Urban Field", "A set of versatile resistance bands for strength sessions at home or away.", "699.00", "899.00", 50, False),
            ("Stainless Steel Shaker", "Sports & Fitness", "Northstar", "A durable shaker bottle with a leak-resistant lid for gym and travel.", "799.00", "999.00", 29, False),
            ("Daily Run Belt", "Sports & Fitness", "Urban Field", "A low-profile running belt that keeps small essentials secure while moving.", "599.00", "799.00", 34, False),
            ("The Art of Small Habits", "Books", "PageTurner", "A practical sample title about building thoughtful, sustainable everyday routines.", "399.00", "499.00", 24, True),
            ("A Journey Through India", "Books", "PageTurner", "A richly illustrated sample travel book celebrating landscapes and local stories.", "649.00", "799.00", 16, False),
            ("The Curious Garden", "Books", "PageTurner", "A charming sample illustrated story for curious young readers and families.", "299.00", "399.00", 40, False),
            ("Creative Building Blocks", "Toys & Games", "Everyday Co.", "A colourful construction set encouraging open-ended play and creative thinking.", "1199.00", "1499.00", 23, True),
            ("Family Strategy Game", "Toys & Games", "Brightside", "A friendly strategy board game designed for shared family game nights.", "899.00", "1199.00", 18, False),
            ("Wooden Puzzle Set", "Toys & Games", "Aster & Oak", "A tactile wooden puzzle set for relaxed, screen-free play and problem solving.", "749.00", "999.00", 22, False),
            ("Pantry Starter Box", "Grocery & Essentials", "Everyday Co.", "A convenient selection of shelf-stable pantry staples for everyday cooking.", "899.00", "1099.00", 48, True),
            ("Reusable Food Storage Set", "Grocery & Essentials", "Aster & Oak", "Reusable kitchen storage essentials for keeping everyday ingredients organised.", "599.00", "799.00", 33, False),
            ("Organic Tea Discovery Pack", "Grocery & Essentials", "Brightside", "A sample assortment of aromatic teas for a calm daily tea break.", "449.00", "599.00", 39, False),
            ("Cotton Kitchen Towel Set", "Home & Kitchen", "Aster & Oak", "Absorbent cotton towels in a neutral palette for practical everyday kitchens.", "499.00", "649.00", 30, False),
        ]
        image_ids = [
                '1511707171634-5f897ff02aa9', '1496181133206-80ce9b88a853', '1505740420928-5e560c06d30e',
                '1523275335684-37898b6baf30', '1608043152269-423dbba4e7e1', '1587829741301-dc798b83add3',
                '1596755094514-f87e34085b2c', '1542291026-7eec264c27ff', '1553062407-98eeb64c6a62',
                '1576566588028-4147f3842f27', '1602143407151-7111542de6e8', '1603199506016-b9a594b593c0',
                '1645334249846-9df5bce6a1a7', '1495474472287-4d71bcdd2085', '1608248543803-ba4f8c70ae0b',
                '1556229010-6c3f2c9ca5f8', '1556228720-195a672e8a03', '1608248543803-ba4f8c70ae0b',
                '1544367567-0f2fcb009e0b', '1598289431512-b97b0917affc', '1579758629938-03607ccdbaba',
                '1533561052604-c3beb6d55b8d', '1544947950-fa07a98d237f', '1519682337058-a94d519337bc',
                '1512820790803-83ca734da794', '1587654780291-39c9404d746b', '1610890716171-6b1bb98ffd09',
                '1603052875302-d376b7c0638a', '1543168256-418811576931', '1602143407151-7111542de6e8',
                '1544787219-7f47ccb76574', '1603199506016-b9a594b593c0',
        ]
        for index, (name, category, brand, description, price, original, stock, featured) in enumerate(catalog):
            image = f"https://images.unsplash.com/photo-{image_ids[index]}?auto=format&fit=crop&w=900&q=85"
            product, _ = Product.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "category": category_objects[category],
                    "brand": brands[brand],
                    "description": description,
                    "specifications": {"Material": "Quality-tested materials", "Warranty": "1 year limited warranty"},
                    "price": Decimal(price),
                    "original_price": Decimal(original),
                    "stock": stock,
                    "rating": Decimal("4.00"),
                    "review_count": 0,
                    "image_url": image,
                    "is_featured": featured,
                    "is_active": True,
                    "popularity": 100 - index,
                },
            )
            ProductReview.objects.get_or_create(
                product=product,
                user=reviewer,
                defaults={
                    "rating": 4,
                    "title": "Demonstration feedback",
                    "body": "This sample review is demonstration content, not a genuine customer review.",
                    "is_demo": True,
                },
            )
            Product.objects.filter(pk=product.pk).update(rating=Decimal("4.00"), review_count=1)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(catalog)} ShopSphere demo products, {len(categories)} categories, and labelled sample reviews."
        ))
