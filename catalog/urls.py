from django.urls import path, re_path
from . import views

app_name = "catalog"

urlpatterns = [
	path("", views.catalog_home, name="home"),
	re_path(r"^(?P<category_slug>[\w\-]+)/$", views.category_detail, name="category_detail"),
	re_path(r"^(?P<category_slug>[\w\-]+)/(?P<subcategory_slug>[\w\-]+)/$", views.subcategory_detail, name="subcategory_detail"),
]

