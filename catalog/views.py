from django.shortcuts import render, get_object_or_404
from .models import Category, Subcategory


def catalog_home(request):
	"""Main catalog page showing all categories and standalone subcategories."""
	categories = Category.objects.all()
	# Get subcategories without a category (standalone)
	standalone_subcategories = Subcategory.objects.filter(category__isnull=True)
	context = {
		"categories": categories,
		"standalone_subcategories": standalone_subcategories,
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
	"""Subcategory detail page with image gallery."""
	category = get_object_or_404(Category, slug=category_slug)
	subcategory = get_object_or_404(Subcategory, category=category, slug=subcategory_slug)
	# Get all categories for navigation
	all_categories = Category.objects.all()
	# Get all subcategory images
	subcategory_images = subcategory.images.all()
	
	context = {
		"category": category,
		"subcategory": subcategory,
		"subcategory_images": subcategory_images,
		"all_categories": all_categories,
	}
	return render(request, "catalog/subcategory_detail.html", context)


def standalone_subcategory_detail(request, subcategory_slug):
	"""Standalone subcategory detail page (without category)."""
	subcategory = get_object_or_404(Subcategory, slug=subcategory_slug, category__isnull=True)
	# Get all categories for navigation
	all_categories = Category.objects.all()
	# Get all subcategory images
	subcategory_images = subcategory.images.all()
	
	context = {
		"category": None,
		"subcategory": subcategory,
		"subcategory_images": subcategory_images,
		"all_categories": all_categories,
	}
	return render(request, "catalog/subcategory_detail.html", context)
