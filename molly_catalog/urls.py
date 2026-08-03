from django.urls import path, re_path
from . import views

app_name = "molly_catalog"

urlpatterns = [
    path("", views.catalog_home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Cart
    path("cart/", views.cart_view, name="cart"),
    path("cart/drawer/", views.cart_drawer, name="cart_drawer"),
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/add-bulk/", views.cart_add_bulk, name="cart_add_bulk"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    # Checkout & orders
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<str:order_number>/", views.order_confirm, name="order_confirm"),
    # Mockup studio (הדמיות) – must come before the category catch-all
    path("mockups/", views.mockup_studio, name="mockups"),
    path("mockups/save/", views.mockup_save, name="mockup_save"),
    path("mockups/<int:mockup_id>/delete/", views.mockup_delete, name="mockup_delete"),
    # Standalone product detail (no category) – must come before category_detail
    re_path(r"^product/(?P<product_slug>[\w\-]+)/$", views.product_detail, name="standalone_product_detail"),
    re_path(r"^(?P<category_slug>[\w\-]+)/$", views.category_detail, name="category_detail"),
    re_path(r"^(?P<category_slug>[\w\-]+)/(?P<product_slug>[\w\-]+)/$", views.product_detail, name="category_product_detail"),
]
