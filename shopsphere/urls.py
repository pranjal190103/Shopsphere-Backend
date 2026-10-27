from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from store.views import (
    AddressViewSet,
    BrandListView,
    CartView,
    CategoryListView,
    LoginView,
    OrderViewSet,
    ProductViewSet,
    ProfileView,
    RefreshView,
    RegisterView,
    WishlistView,
)

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("addresses", AddressViewSet, basename="address")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/register/", RegisterView.as_view(), name="register"),
    path("api/v1/auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", RefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/profile/", ProfileView.as_view(), name="profile"),
    path("api/v1/categories/", CategoryListView.as_view(), name="categories"),
    path("api/v1/brands/", BrandListView.as_view(), name="brands"),
    path("api/v1/cart/", CartView.as_view(), name="cart"),
    path("api/v1/cart/items/", CartView.as_view(), name="cart-items"),
    path("api/v1/cart/items/<int:item_id>/", CartView.as_view(), name="cart-item"),
    path("api/v1/wishlist/", WishlistView.as_view(), name="wishlist"),
    path("api/v1/wishlist/items/", WishlistView.as_view(), name="wishlist-items"),
    path("api/v1/wishlist/items/<int:item_id>/", WishlistView.as_view(), name="wishlist-item"),
    path("api/v1/", include(router.urls)),
]
