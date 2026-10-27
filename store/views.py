import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Address, Brand, Cart, CartItem, Category, Order, OrderItem, Product, ProductReview, Wishlist, WishlistItem
from .serializers import (
    AddressSerializer,
    BrandSerializer,
    CartItemSerializer,
    CategorySerializer,
    OrderSerializer,
    ProductSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ReviewSerializer,
    WishlistItemSerializer,
)


class AuthThrottle(AnonRateThrottle):
    scope = "auth"


class LoginView(TokenObtainPairView):
    throttle_classes = [AuthThrottle]


class RefreshView(TokenRefreshView):
    throttle_classes = [AuthThrottle]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by("name")


class BrandListView(generics.ListAPIView):
    serializer_class = BrandSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Brand.objects.filter(products__is_active=True).distinct().order_by("name")


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["price", "rating", "created_at", "popularity", "name"]
    ordering = ["-is_featured", "-created_at"]

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related("brand", "category").prefetch_related("images")
        params = self.request.query_params
        ids = params.get("ids")
        if ids:
            try:
                product_ids = [int(value) for value in ids.split(",") if value]
                if len(product_ids) > 20:
                    raise ValueError
                queryset = queryset.filter(id__in=product_ids)
            except ValueError:
                raise ValidationError({"ids": "Provide a comma-separated list of up to 20 product IDs."})
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search) | Q(brand__name__icontains=search))
        category = params.get("category")
        if category:
            queryset = queryset.filter(Q(category__slug=category) | Q(category__name__iexact=category))
        brand = params.get("brand")
        if brand:
            queryset = queryset.filter(Q(brand__slug=brand) | Q(brand__name__iexact=brand))
        for key, lookup in (("min_price", "price__gte"), ("max_price", "price__lte"), ("min_rating", "rating__gte")):
            value = params.get(key)
            if value:
                try:
                    number = Decimal(value)
                    if number < 0:
                        raise ValueError
                    queryset = queryset.filter(**{lookup: number})
                except (ValueError, ArithmeticError):
                    raise ValidationError({key: "Enter a valid non-negative number."})
        in_stock = params.get("in_stock")
        if in_stock in ("true", "1"):
            queryset = queryset.filter(stock__gt=0)
        elif in_stock in ("false", "0"):
            queryset = queryset.filter(stock=0)
        if params.get("deals") in ("true", "1"):
            queryset = queryset.filter(original_price__gt=F("price"))
        return queryset

    @action(detail=False, methods=["get"])
    def featured(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(is_featured=True))
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=False, methods=["get"])
    def deals(self, request):
        queryset = self.filter_queryset(self.get_queryset()).filter(original_price__gt=F("price")).order_by("-popularity")
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        return self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="reviews")
    def reviews(self, request, slug=None):
        product = self.get_object()
        if request.method == "GET":
            reviews = product.reviews.all()
            return Response(ReviewSerializer(reviews, many=True).data)
        if not request.user.is_authenticated:
            return Response({"detail": "Sign in to write a review."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                review = serializer.save(product=product, user=request.user)
                reviews = list(product.reviews.all())
                count = len(reviews)
                average = sum((item.rating for item in reviews), 0) / count if count else 0
                Product.objects.filter(pk=product.pk).update(
                    rating=Decimal(str(average)).quantize(Decimal("0.01")),
                    review_count=count,
                )
        except IntegrityError:
            raise ValidationError({"detail": "You have already reviewed this product."})
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, item_id=None):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = cart.items.select_related("product", "product__brand", "product__category").prefetch_related("product__images")
        subtotal = sum((item.product.price * item.quantity for item in items), Decimal("0.00"))
        shipping = Decimal("0.00") if subtotal == 0 or subtotal >= Decimal("999.00") else Decimal("49.00")
        return Response({"items": CartItemSerializer(items, many=True).data, "subtotal": subtotal, "shipping": shipping, "total": subtotal + shipping})

    def post(self, request, item_id=None):
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]
        if quantity > product.stock:
            raise ValidationError({"quantity": f"Only {product.stock} units are currently available."})
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"quantity": quantity})
        if not created:
            if item.quantity + quantity > product.stock:
                raise ValidationError({"quantity": f"Only {product.stock - item.quantity} additional units are available."})
            item.quantity += quantity
            item.save(update_fields=["quantity", "updated_at"])
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def patch(self, request, item_id=None):
        item = get_object_or_404(CartItem.objects.select_related("product", "cart"), pk=item_id, cart__user=request.user)
        quantity = request.data.get("quantity")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValidationError({"quantity": "Enter a whole number greater than zero."})
        if quantity > item.product.stock:
            raise ValidationError({"quantity": f"Only {item.product.stock} units are currently available."})
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])
        return Response(CartItemSerializer(item).data)

    def delete(self, request, item_id=None):
        if not item_id:
            raise ValidationError({"detail": "A cart item id is required."})
        item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WishlistView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, item_id=None):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        items = wishlist.items.select_related("product", "product__brand", "product__category").prefetch_related("product__images")
        return Response(WishlistItemSerializer(items, many=True).data)

    def post(self, request, item_id=None):
        serializer = WishlistItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        item, _ = WishlistItem.objects.get_or_create(wishlist=wishlist, product=serializer.validated_data["product"])
        return Response(WishlistItemSerializer(item).data, status=status.HTTP_201_CREATED)

    def delete(self, request, item_id=None):
        if item_id is None:
            raise ValidationError({"detail": "A wishlist item id is required."})
        item = get_object_or_404(WishlistItem, pk=item_id, wishlist__user=request.user)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if serializer.validated_data.get("is_default"):
            Address.objects.filter(user=self.request.user).update(is_default=False)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.validated_data.get("is_default"):
            Address.objects.filter(user=self.request.user).update(is_default=False)
        serializer.save()


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    def create(self, request, *args, **kwargs):
        address = get_object_or_404(Address, pk=request.data.get("address_id"), user=request.user)
        method = request.data.get("payment_method")
        if method not in ("cod", "demo_card"):
            raise ValidationError({"payment_method": "Choose Cash on Delivery or the simulated demo card option."})
        shipping_method = request.data.get("shipping_method", "standard")
        if shipping_method not in ("standard", "express"):
            raise ValidationError({"shipping_method": "Choose standard or express delivery."})
        with transaction.atomic():
            cart, _ = Cart.objects.get_or_create(user=request.user)
            cart_items = list(cart.items.select_related("product").select_for_update())
            if not cart_items:
                raise ValidationError({"detail": "Your cart is empty."})
            subtotal = Decimal("0.00")
            for item in cart_items:
                product = Product.objects.select_for_update().get(pk=item.product_id)
                if not product.is_active:
                    raise ValidationError({"detail": f"{product.name} is no longer available."})
                if item.quantity > product.stock:
                    raise ValidationError({"detail": f"Only {product.stock} units of {product.name} are available."})
                subtotal += product.price * item.quantity
            shipping = (
                Decimal("149.00")
                if shipping_method == "express"
                else Decimal("0.00") if subtotal >= Decimal("999.00") else Decimal("49.00")
            )
            reference = f"SS-{uuid.uuid4().hex[:10].upper()}"
            address_data = {field: getattr(address, field) for field in ("full_name", "phone", "line1", "line2", "city", "state", "postal_code", "country")}
            order = Order.objects.create(
                user=request.user,
                reference=reference,
                payment_method=method,
                shipping_method=shipping_method,
                payment_status="pending",
                subtotal=subtotal,
                shipping=shipping,
                total=subtotal + shipping,
                address_snapshot=address_data,
            )
            for item in cart_items:
                product = Product.objects.select_for_update().get(pk=item.product_id)
                OrderItem.objects.create(order=order, product=product, product_name=product.name, unit_price=product.price, quantity=item.quantity)
                Product.objects.filter(pk=product.pk).update(stock=F("stock") - item.quantity)
            cart.items.all().delete()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            order = get_object_or_404(Order.objects.select_for_update(), pk=pk, user=request.user)
            if order.status not in ("pending", "confirmed"):
                raise ValidationError({"detail": "This order can no longer be cancelled."})
            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])
            for item in order.items.all():
                Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
        return Response(OrderSerializer(order).data)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Customers cannot update order or payment status."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    partial_update = update

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
