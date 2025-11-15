from django.shortcuts import render, get_object_or_404
from .models import WhiteCategory, WhiteSubcategory


def catalog_home(request):
	"""Main white catalog page showing all categories and standalone subcategories."""
	categories = WhiteCategory.objects.all()
	# Get subcategories without a category (standalone)
	standalone_subcategories = WhiteSubcategory.objects.filter(category__isnull=True)
	context = {
		"categories": categories,
		"standalone_subcategories": standalone_subcategories,
		"all_categories": categories,  # For header navigation
	}
	return render(request, "white_catalog/catalog_home.html", context)


def category_detail(request, category_slug):
	"""Category detail page showing subcategories."""
	category = get_object_or_404(WhiteCategory, slug=category_slug)
	subcategories = category.subcategories.all()
	# Get all categories for navigation
	all_categories = WhiteCategory.objects.all()
	# Get standalone subcategories for navigation
	standalone_subcategories = WhiteSubcategory.objects.filter(category__isnull=True)
	
	context = {
		"category": category,
		"subcategories": subcategories,
		"all_categories": all_categories,
		"standalone_subcategories": standalone_subcategories,
	}
	return render(request, "white_catalog/category_detail.html", context)


def subcategory_detail(request, category_slug, subcategory_slug):
	"""Subcategory detail page with image gallery."""
	category = get_object_or_404(WhiteCategory, slug=category_slug)
	subcategory = get_object_or_404(WhiteSubcategory, category=category, slug=subcategory_slug)
	# Get all categories for navigation
	all_categories = WhiteCategory.objects.all()
	# Get standalone subcategories for navigation
	standalone_subcategories = WhiteSubcategory.objects.filter(category__isnull=True)
	# Get all subcategory images
	subcategory_images = subcategory.images.all()
	
	context = {
		"category": category,
		"subcategory": subcategory,
		"subcategory_images": subcategory_images,
		"all_categories": all_categories,
		"standalone_subcategories": standalone_subcategories,
	}
	return render(request, "white_catalog/subcategory_detail.html", context)


def standalone_subcategory_detail(request, subcategory_slug):
	"""Standalone subcategory detail page (without category)."""
	subcategory = get_object_or_404(WhiteSubcategory, slug=subcategory_slug, category__isnull=True)
	# Get all categories for navigation
	all_categories = WhiteCategory.objects.all()
	# Get standalone subcategories for navigation
	standalone_subcategories = WhiteSubcategory.objects.filter(category__isnull=True)
	# Get all subcategory images
	subcategory_images = subcategory.images.all()
	
	context = {
		"category": None,
		"subcategory": subcategory,
		"subcategory_images": subcategory_images,
		"all_categories": all_categories,
		"standalone_subcategories": standalone_subcategories,
	}
	return render(request, "white_catalog/subcategory_detail.html", context)

