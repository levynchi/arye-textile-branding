from django.contrib import admin
from .models import Category, Subcategory, Product


class SubcategoryInline(admin.TabularInline):
	"""Inline admin for Subcategory within Category."""
	model = Subcategory
	extra = 1
	fields = ("name", "description", "image", "order", "slug")
	prepopulated_fields = {"slug": ("name",)}


class ProductInline(admin.TabularInline):
	"""Inline admin for Product within Subcategory."""
	model = Product
	extra = 1
	fields = ("name", "description", "image", "order", "is_active", "slug")
	prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	"""Admin interface for Category model."""
	list_display = ("name", "order", "created", "updated")
	list_editable = ("order",)
	search_fields = ("name", "description")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")
	inlines = [SubcategoryInline]
	
	fieldsets = (
		(None, {
			"fields": ("name", "slug", "description", "image", "order")
		}),
		("מידע נוסף", {
			"fields": ("created", "updated"),
			"classes": ("collapse",)
		}),
	)


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
	"""Admin interface for Subcategory model."""
	list_display = ("name", "category", "order", "created", "updated")
	list_editable = ("order",)
	list_filter = ("category",)
	search_fields = ("name", "description", "category__name")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")
	inlines = [ProductInline]
	
	fieldsets = (
		(None, {
			"fields": ("category", "name", "slug", "description", "image", "order")
		}),
		("מידע נוסף", {
			"fields": ("created", "updated"),
			"classes": ("collapse",)
		}),
	)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	"""Admin interface for Product model."""
	list_display = ("name", "subcategory", "is_active", "order", "created", "updated")
	list_editable = ("order", "is_active")
	list_filter = ("is_active", "subcategory__category", "subcategory")
	search_fields = ("name", "description", "subcategory__name")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")
	
	fieldsets = (
		(None, {
			"fields": ("subcategory", "name", "slug", "description", "image", "order", "is_active")
		}),
		("מידע נוסף", {
			"fields": ("created", "updated"),
			"classes": ("collapse",)
		}),
	)
