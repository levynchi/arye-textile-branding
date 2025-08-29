from django.contrib import admin
from .models import Gallery, Banner, ContactRequest, Slide


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "updated")
	readonly_fields = ("updated",)
	fieldsets = (
		(None, {"fields": ("title",)}),
		("קטגוריות", {
			"fields": (
				("image1", "caption1"),
				("image2", "caption2"),
				("image3", "caption3"),
				("image4", "caption4"),
				("image5", "caption5"),
				("image6", "caption6"),
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
	fields = ("page", "image", "updated")

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
