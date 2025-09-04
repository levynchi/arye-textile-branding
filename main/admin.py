from django.contrib import admin
from django.utils.html import format_html
from django.shortcuts import redirect
from django.urls import reverse
from .models import Gallery, Banner, ContactRequest, Slide, BrandingGallery, PrintingGallery, PatternmakingGallery, FabricsGallery, ManufacturingGallery, FooterSettings, PhotosGallery


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

	def changelist_view(self, request, extra_context=None):
		"""Redirect the gallery list to the single instance change form.

		Ensures a singleton: creates one if not exists and sends the user
		straight to its change page.
		"""
		obj = Gallery.objects.order_by("id").first()
		if obj is None:
			obj = Gallery.objects.create(title="גלריה לבית")
		url = reverse("admin:main_gallery_change", args=[obj.pk])
		return redirect(url)

	def has_add_permission(self, request):
		"""Allow adding only if no instance exists."""
		return Gallery.objects.count() == 0

	def has_delete_permission(self, request, obj=None):
		"""Prevent deleting the singleton from the admin UI."""
		return False


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
	list_display = ("id", "thumb", "order", "alt", "created")
	list_editable = ("order",)
	ordering = ("order", "id")

	@admin.display(description="תמונה")
	def thumb(self, obj: Slide):  # type: ignore[name-defined]
		if getattr(obj, "image", None) and obj.image:
			try:
				url = obj.image.url
			except Exception:
				return "—"
			alt = obj.alt or ""
			return format_html(
				'<img src="{}" alt="{}" style="height:60px;width:auto;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.2);"/>',
				url,
				alt,
			)
		return "—"


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


@admin.register(PrintingGallery)
class PrintingGalleryAdmin(admin.ModelAdmin):
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	fieldsets = (
		(None, {
			"fields": (
				("image1", "image2", "image3"),
				("image4", "image5", "image6"),
				("image7", "image8", "image9"),
				("image10", "image11", "image12"),
				"updated",
			)
		}),
	)

	def changelist_view(self, request, extra_context=None):
		"""Redirect to the single instance change form (singleton)."""
		obj = PrintingGallery.objects.order_by("id").first()
		if obj is None:
			obj = PrintingGallery.objects.create()
		url = reverse("admin:main_printinggallery_change", args=[obj.pk])
		return redirect(url)

	def has_add_permission(self, request):
		return PrintingGallery.objects.count() == 0

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(PatternmakingGallery)
class PatternmakingGalleryAdmin(admin.ModelAdmin):
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
		obj = PatternmakingGallery.objects.order_by("id").first()
		if obj is None:
			obj = PatternmakingGallery.objects.create()
		url = reverse("admin:main_patternmakinggallery_change", args=[obj.pk])
		return redirect(url)

	def has_add_permission(self, request):
		return PatternmakingGallery.objects.count() == 0

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(FabricsGallery)
class FabricsGalleryAdmin(admin.ModelAdmin):
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
		obj = FabricsGallery.objects.order_by("id").first()
		if obj is None:
			obj = FabricsGallery.objects.create()
		url = reverse("admin:main_fabricsgallery_change", args=[obj.pk])
		return redirect(url)

	def has_add_permission(self, request):
		return FabricsGallery.objects.count() == 0

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(ManufacturingGallery)
class ManufacturingGalleryAdmin(admin.ModelAdmin):
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
		obj = ManufacturingGallery.objects.order_by("id").first()
		if obj is None:
			obj = ManufacturingGallery.objects.create()
		url = reverse("admin:main_manufacturinggallery_change", args=[obj.pk])
		return redirect(url)

	def has_add_permission(self, request):
		return ManufacturingGallery.objects.count() == 0

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(FooterSettings)
class FooterSettingsAdmin(admin.ModelAdmin):
	list_display = ("id", "phone_display", "email", "updated")
	readonly_fields = ("updated",)
	fields = ("phone_display", "email", "whatsapp_link", "instagram_url", "facebook_url", "updated")

	def changelist_view(self, request, extra_context=None):
		obj = FooterSettings.objects.order_by("id").first()
		if obj is None:
			obj = FooterSettings.objects.create(phone_display="054-2367535")
		url = reverse("admin:main_footersettings_change", args=[obj.pk])
		return redirect(url)

	def has_add_permission(self, request):
		return FooterSettings.objects.count() == 0

	def has_delete_permission(self, request, obj=None):
		return False


	@admin.register(PhotosGallery)
	class PhotosGalleryAdmin(admin.ModelAdmin):
		list_display = ("id", "updated")
		readonly_fields = ("updated",)
		fieldsets = (
			(None, {
				"fields": (
					("image1", "image2", "image3"),
					("image4", "image5", "image6"),
					("image7", "image8", "image9"),
					("image10", "image11", "image12"),
					"updated",
				)
			}),
		)

		def changelist_view(self, request, extra_context=None):
			obj = PhotosGallery.objects.order_by("id").first()
			if obj is None:
				obj = PhotosGallery.objects.create()
			url = reverse("admin:main_photosgallery_change", args=[obj.pk])
			return redirect(url)

		def has_add_permission(self, request):
			return PhotosGallery.objects.count() == 0

		def has_delete_permission(self, request, obj=None):
			return False
