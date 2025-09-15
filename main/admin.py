from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import models as dj_models
from django.db.utils import ProgrammingError, OperationalError
from .models import (
	Gallery,
	Banner,
	ContactRequest,
	Slide,
	BrandingGallery,
	PrintingGallery,
	PatternmakingGallery,
	FabricsGallery,
	ManufacturingGallery,
	CuttingGallery,
	FooterSettings,
	PhotosGallery,
	BrandingImage,
	PrintingImage,
	PatternmakingImage,
	FabricsImage,
	ManufacturingImage,
	CuttingImage,
	PhotosImage,
)


class GalleryPreviewForm(forms.ModelForm):
	"""Admin form that shows an inline preview under each ImageField input."""
	preview_max_width = 220
	preview_max_height = 160

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		instance = getattr(self, "instance", None)
		if not instance:
			return
		# Iterate over bound fields and attach preview in help_text for ImageFields
		for name, field in self.fields.items():
			try:
				model_field = self._meta.model._meta.get_field(name)
			except Exception:
				continue
			if isinstance(model_field, dj_models.ImageField):
				file = getattr(instance, name, None)
				if file:
					try:
						url = file.url
					except Exception:
						continue
					preview_html = (
						f'<div style="margin-top:6px">'
						f'<img src="{url}" alt="preview" '
						f'style="display:block;max-width:{self.preview_max_width}px;max-height:{self.preview_max_height}px;'
						f'border-radius:4px;box-shadow:0 0 2px rgba(0,0,0,.2)"/>'
						f"</div>"
					)
					# Preserve existing help_text if any
					if field.help_text:
						field.help_text = mark_safe(str(field.help_text) + preview_html)
					else:
						field.help_text = mark_safe(preview_html)


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
	form = GalleryPreviewForm
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
	list_display = ("id", "page", "has_video", "has_image", "updated")
	list_filter = ("page",)
	search_fields = ("page",)
	readonly_fields = ("updated",)
	fields = ("page", "image", "video", "height_variant", "updated")
	
	@admin.display(boolean=True, description="יש וידיאו")
	def has_video(self, obj):
		return bool(obj.video)
	
	@admin.display(boolean=True, description="יש תמונה")
	def has_image(self, obj):
		return bool(obj.image)

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
	form = GalleryPreviewForm
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	class ImageInline(admin.TabularInline):
		model = BrandingImage
		extra = 1
		fields = ("preview", "image", "alt", "order",)
		readonly_fields = ("preview",)

		def preview(self, obj):
			if getattr(obj, "image", None):
				try:
					url = obj.image.url
				except Exception:
					return "—"
				return format_html('<img src="{}" style="height:60px;width:auto;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.2);"/>', url)
			return "—"

	inlines = [ImageInline]
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
	form = GalleryPreviewForm
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	class ImageInline(admin.TabularInline):
		model = PrintingImage
		extra = 1
		fields = ("preview", "image", "alt", "order",)
		readonly_fields = ("preview",)

		def preview(self, obj):
			if getattr(obj, "image", None):
				try:
					url = obj.image.url
				except Exception:
					return "—"
				return format_html('<img src="{}" style="height:60px;width:auto;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.2);"/>', url)
			return "—"

	inlines = [ImageInline]
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
	form = GalleryPreviewForm
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	class ImageInline(admin.TabularInline):
		model = PatternmakingImage
		extra = 1
		fields = ("preview", "image", "alt", "order",)
		readonly_fields = ("preview",)

		def preview(self, obj):
			if getattr(obj, "image", None):
				try:
					url = obj.image.url
				except Exception:
					return "—"
				return format_html('<img src="{}" style="height:60px;width:auto;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.2);"/>', url)
			return "—"

	inlines = [ImageInline]
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
	form = GalleryPreviewForm
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	class ImageInline(admin.TabularInline):
		model = FabricsImage
		extra = 1
		fields = ("preview", "image", "alt", "order",)
		readonly_fields = ("preview",)

		def preview(self, obj):
			if getattr(obj, "image", None):
				try:
					url = obj.image.url
				except Exception:
					return "—"
				return format_html('<img src="{}" style="height:60px;width:auto;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.2);"/>', url)
			return "—"

	inlines = [ImageInline]
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
	form = GalleryPreviewForm
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	class ImageInline(admin.TabularInline):
		model = ManufacturingImage
		extra = 1
		fields = ("preview", "image", "alt", "order",)
		readonly_fields = ("preview",)

		def preview(self, obj):
			if getattr(obj, "image", None):
				try:
					url = obj.image.url
				except Exception:
					return "—"
				return format_html('<img src="{}" style="height:60px;width:auto;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.2);"/>', url)
			return "—"

	inlines = [ImageInline]
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



@admin.register(CuttingGallery)
class CuttingGalleryAdmin(admin.ModelAdmin):
	form = GalleryPreviewForm
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	class ImageInline(admin.TabularInline):
		model = CuttingImage
		extra = 1
		fields = ("preview", "image", "alt", "order",)
		readonly_fields = ("preview",)

		def preview(self, obj):
			if getattr(obj, "image", None):
				try:
					url = obj.image.url
				except Exception:
					return "—"
				return format_html('<img src="{}" style="height:60px;width:auto;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.2);"/>', url)
			return "—"

	inlines = [ImageInline]
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
		obj = CuttingGallery.objects.order_by("id").first()
		if obj is None:
			obj = CuttingGallery.objects.create()
		url = reverse("admin:main_cuttinggallery_change", args=[obj.pk])
		return redirect(url)

	def has_add_permission(self, request):
		return CuttingGallery.objects.count() == 0

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(PhotosGallery)
class PhotosGalleryAdmin(admin.ModelAdmin):
	form = GalleryPreviewForm
	list_display = ("id", "updated")
	readonly_fields = ("updated",)
	class ImageInline(admin.TabularInline):
		model = PhotosImage
		extra = 1
		fields = ("preview", "image", "alt", "order",)
		readonly_fields = ("preview",)

		def preview(self, obj):
			if getattr(obj, "image", None):
				try:
					url = obj.image.url
				except Exception:
					return "—"
				return format_html('<img src="{}" style="height:60px;width:auto;border-radius:2px;box-shadow:0 0 2px rgba(0,0,0,.2);"/>', url)
			return "—"

	inlines = [ImageInline]
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
		try:
			return PhotosGallery.objects.count() == 0
		except (ProgrammingError, OperationalError):
			# Table not created yet in this environment; allow add to avoid crash
			return True

	def has_delete_permission(self, request, obj=None):
		return False
