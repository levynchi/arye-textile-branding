from django.urls import path, re_path
from . import views

app_name = "white_catalog"

urlpatterns = [
    path("", views.catalog_home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("search/", views.barcode_search, name="barcode_search"),
    # Cart
    path("cart/", views.cart_view, name="cart"),
    path("cart/drawer/", views.cart_drawer, name="cart_drawer"),
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    # Checkout & orders
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("orders/<str:order_number>/export/", views.export_order_excel, name="export_order"),
    path("orders/<str:order_number>/", views.order_confirm, name="order_confirm"),
    # Product data export for customer site integration
    path("export/products/", views.export_products_excel, name="export_products"),
    # Standalone subcategory — must come before category_detail
    re_path(r"^product/(?P<subcategory_slug>[\w\-]+)/$", views.standalone_subcategory_detail, name="standalone_subcategory_detail"),
    re_path(r"^(?P<category_slug>[\w\-]+)/$", views.category_detail, name="category_detail"),
    re_path(r"^(?P<category_slug>[\w\-]+)/(?P<subcategory_slug>[\w\-]+)/$", views.subcategory_detail, name="subcategory_detail"),
]

