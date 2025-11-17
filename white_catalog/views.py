from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import WhiteCategory, WhiteSubcategory, WhiteCatalogUser


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


def login_view(request):
	"""Login view for white catalog users."""
	if request.method == "POST":
		username = request.POST.get("username", "").strip()
		password = request.POST.get("password", "")
		
		if not username or not password:
			messages.error(request, "נא למלא שם משתמש וסיסמא")
		else:
			try:
				user = WhiteCatalogUser.objects.get(username=username, is_active=True)
				if user.check_password(password):
					# Login successful - store user ID in session
					request.session["white_catalog_user_id"] = user.id
					request.session["white_catalog_username"] = user.username
					request.session["white_catalog_company_name"] = user.company_name
					messages.success(request, f"ברוך הבא, {user.company_name}!")
					
					# Redirect to next page or home
					next_url = request.GET.get("next") or request.POST.get("next") or "white_catalog:home"
					return redirect(next_url)
				else:
					messages.error(request, "שם משתמש או סיסמא שגויים")
			except WhiteCatalogUser.DoesNotExist:
				messages.error(request, "שם משתמש או סיסמא שגויים")
	
	# Get all categories for navigation
	all_categories = WhiteCategory.objects.all()
	standalone_subcategories = WhiteSubcategory.objects.filter(category__isnull=True)
	
	context = {
		"all_categories": all_categories,
		"standalone_subcategories": standalone_subcategories,
	}
	return render(request, "white_catalog/login.html", context)


def logout_view(request):
	"""Logout view for white catalog users."""
	# Remove user data from session
	if "white_catalog_user_id" in request.session:
		del request.session["white_catalog_user_id"]
	if "white_catalog_username" in request.session:
		del request.session["white_catalog_username"]
	if "white_catalog_company_name" in request.session:
		del request.session["white_catalog_company_name"]
	
	messages.success(request, "התנתקת בהצלחה")
	return redirect("white_catalog:home")

