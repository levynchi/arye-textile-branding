from django.shortcuts import render, get_object_or_404
from .models import Category, Subcategory, Product


def catalog_home(request):
	"""Main catalog page showing all categories."""
	categories = Category.objects.all()
	context = {
		"categories": categories,
		"all_categories": categories,  # For header navigation
	}
	return render(request, "catalog/catalog_home.html", context)


def category_detail(request, category_slug):
	"""Category detail page showing subcategories."""
	category = get_object_or_404(Category, slug=category_slug)
	subcategories = category.subcategories.all()
	# Get all categories for navigation
	all_categories = Category.objects.all()
	
	context = {
		"category": category,
		"subcategories": subcategories,
		"all_categories": all_categories,
	}
	return render(request, "catalog/category_detail.html", context)


def subcategory_detail(request, category_slug, subcategory_slug):
	"""Subcategory detail page showing products."""
	category = get_object_or_404(Category, slug=category_slug)
	subcategory = get_object_or_404(Subcategory, category=category, slug=subcategory_slug)
	products = subcategory.products.filter(is_active=True)
	# Get all categories for navigation
	all_categories = Category.objects.all()
	
	context = {
		"category": category,
		"subcategory": subcategory,
		"products": products,
		"all_categories": all_categories,
	}
	return render(request, "catalog/subcategory_detail.html", context)
