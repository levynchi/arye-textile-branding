from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from .models import Gallery, Banner, ContactRequest, Slide, BrandingGallery


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "updated")
	readonly_fields = ("updated",)
	fieldsets = (
		(None, {"fields": ("title",)}),
		("קטגוריות", {
			"fields": (
				("image1", "caption1", "link1"),
				("image2", "caption2", "link2"),
				("image3", "caption3", "link3"),
				("image4", "caption4", "link4"),
				("image5", "caption5", "link5"),
				("image6", "caption6", "link6"),
				"updated",
			)
		}),
	)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
	list_display = ("id", "page", "updated")
	list_filter = ("page",)
	search_fields = ("page",)
	readonly_fields = ("updated",)
	fields = ("page", "image", "height_variant", "updated")

# Register your models here.

@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
	list_display = ("id", "full_name", "email", "phone", "created", "answered")
	list_filter = ("answered", "created")
	search_fields = ("full_name", "email", "phone", "company")
	readonly_fields = ("created",)

@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
	list_display = ("id", "order", "alt", "created")
	list_editable = ("order",)
	ordering = ("order", "id")


@admin.register(BrandingGallery)
class BrandingGalleryAdmin(admin.ModelAdmin):
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	fieldsets = (
		(None, {
			"fields": (
				("image1", "image2", "image3"),
				("image4", "image5", "image6"),
				("image7", "image8", "image9"),
				"updated",
			)
		}),
	)

	def changelist_view(self, request, extra_context=None):
		"""Redirect the changelist to the single instance change form.

		Ensures a singleton: creates one if not exists and sends the user
		straight to its change page.
		"""
		obj = BrandingGallery.objects.order_by("id").first()
		if obj is None:
			obj = BrandingGallery.objects.create()
		url = reverse("admin:main_brandinggallery_change", args=[obj.pk])
		return redirect(url)

	def has_add_permission(self, request):
		"""Allow adding only if no instance exists."""
		return BrandingGallery.objects.count() == 0

	def has_delete_permission(self, request, obj=None):
		"""Prevent deleting the singleton from the admin UI."""
		return False
