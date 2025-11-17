from django.urls import path, re_path
from . import views

app_name = "white_catalog"

urlpatterns = [
	path("", views.catalog_home, name="home"),
	path("login/", views.login_view, name="login"),
	path("logout/", views.logout_view, name="logout"),
	# Standalone subcategory (without category) - must come before category_detail
	path("product/<slug:subcategory_slug>/", views.standalone_subcategory_detail, name="standalone_subcategory_detail"),
	re_path(r"^(?P<category_slug>[\w\-]+)/$", views.category_detail, name="category_detail"),
	re_path(r"^(?P<category_slug>[\w\-]+)/(?P<subcategory_slug>[\w\-]+)/$", views.subcategory_detail, name="subcategory_detail"),
]

