from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Address, Brand, Cart, CartItem, Category, Order, Product, WishlistItem


class StoreApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="shopper", password="StrongPass123!")
        self.other_user = User.objects.create_user(username="another", password="StrongPass123!")
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.brand = Brand.objects.create(name="Northstar", slug="northstar")
        self.product = Product.objects.create(
            name="Demo Headphones",
            slug="demo-headphones",
            brand=self.brand,
            category=self.category,
            description="A sample product for API tests.",
            price=Decimal("100.00"),
            original_price=Decimal("125.00"),
            stock=5,
        )

    def test_anonymous_users_can_browse_and_filter_products(self):
        response = self.client.get("/api/v1/products/", {"category": "electronics", "min_price": "50"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["slug"], self.product.slug)

    def test_registration_creates_user_with_hashed_password(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {"username": "new-shopper", "email": "new@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        registered = User.objects.get(username="new-shopper")
        self.assertNotEqual(registered.password, "StrongPass123!")
        self.assertTrue(registered.check_password("StrongPass123!"))

    def test_cart_add_merges_duplicate_items_and_rejects_excess_stock(self):
        self.client.force_authenticate(self.user)
        first = self.client.post("/api/v1/cart/items/", {"product_id": self.product.id, "quantity": 2}, format="json")
        second = self.client.post("/api/v1/cart/items/", {"product_id": self.product.id, "quantity": 1}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(CartItem.objects.get(cart__user=self.user).quantity, 3)
        invalid = self.client.post("/api/v1/cart/items/", {"product_id": self.product.id, "quantity": 3}, format="json")
        self.assertEqual(invalid.status_code, 400)
        cart = self.client.get("/api/v1/cart/")
        self.assertEqual(cart.data["subtotal"], Decimal("300.00"))

    def test_order_recalculates_totals_and_decrements_inventory(self):
        self.client.force_authenticate(self.user)
        address = Address.objects.create(
            user=self.user, full_name="Shopper", phone="9999999999", line1="1 Demo Road",
            city="Pune", state="Maharashtra", postal_code="411001",
        )
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        response = self.client.post(
            "/api/v1/orders/",
            {"address_id": address.id, "payment_method": "demo_card", "total": "0.01"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        order = Order.objects.get(reference=response.data["reference"])
        self.assertEqual(order.subtotal, Decimal("200.00"))
        self.assertEqual(order.shipping, Decimal("49.00"))
        self.assertEqual(order.total, Decimal("249.00"))
        self.assertEqual(order.payment_status, "pending")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertFalse(cart.items.exists())

    def test_express_shipping_is_calculated_by_the_backend(self):
        self.client.force_authenticate(self.user)
        address = Address.objects.create(
            user=self.user, full_name="Shopper", phone="9999999999", line1="1 Demo Road",
            city="Pune", state="Maharashtra", postal_code="411001",
        )
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        response = self.client.post(
            "/api/v1/orders/",
            {"address_id": address.id, "payment_method": "cod", "shipping_method": "express", "shipping": "0"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["shipping_method"], "express")
        self.assertEqual(Decimal(response.data["shipping"]), Decimal("149.00"))
        self.assertEqual(Decimal(response.data["total"]), Decimal("249.00"))

    def test_order_rejects_stock_changes_and_other_users_cannot_access_orders(self):
        self.client.force_authenticate(self.user)
        address = Address.objects.create(
            user=self.user, full_name="Shopper", phone="9999999999", line1="1 Demo Road",
            city="Pune", state="Maharashtra", postal_code="411001",
        )
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=4)
        Product.objects.filter(pk=self.product.pk).update(stock=2)
        failed = self.client.post(
            "/api/v1/orders/",
            {"address_id": address.id, "payment_method": "cod"},
            format="json",
        )
        self.assertEqual(failed.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(cart.items.count(), 1)

        order = Order.objects.create(
            user=self.user, reference="SS-PRIVATE-1", payment_method="cod",
            subtotal=Decimal("100.00"), shipping=Decimal("49.00"), total=Decimal("149.00"),
            address_snapshot={"city": "Pune"},
        )
        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.client.get(f"/api/v1/orders/{order.id}/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/orders/").data["count"], 0)
        self.assertEqual(
            self.client.patch(f"/api/v1/orders/{order.id}/", {"payment_status": "paid"}, format="json").status_code,
            405,
        )

    def test_address_resources_are_private_to_the_owner(self):
        address = Address.objects.create(
            user=self.user, full_name="Shopper", phone="9999999999", line1="1 Demo Road",
            city="Pune", state="Maharashtra", postal_code="411001",
        )
        self.client.force_authenticate(self.user)
        updated = self.client.patch(f"/api/v1/addresses/{address.id}/", {"city": "Mumbai"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["city"], "Mumbai")
        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.client.get("/api/v1/addresses/").data["results"], [])
        self.assertEqual(self.client.patch(f"/api/v1/addresses/{address.id}/", {"city": "Mumbai"}).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/addresses/{address.id}/").status_code, 404)

    def test_wishlist_prevents_duplicate_products(self):
        self.client.force_authenticate(self.user)
        first = self.client.post("/api/v1/wishlist/items/", {"product_id": self.product.id}, format="json")
        second = self.client.post("/api/v1/wishlist/items/", {"product_id": self.product.id}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(WishlistItem.objects.filter(wishlist__user=self.user).count(), 1)

    def test_admin_requires_staff_access(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        self.client.force_authenticate(None)
        self.assertTrue(self.client.login(username="shopper", password="StrongPass123!"))
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        admin_user = User.objects.create_user(username="store-admin", password="StrongPass123!", is_staff=True)
        self.client.logout()
        self.assertTrue(self.client.login(username=admin_user.username, password="StrongPass123!"))
        self.assertEqual(self.client.get("/admin/").status_code, 200)
