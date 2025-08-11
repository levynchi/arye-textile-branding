from django.contrib import admin
from .models import Gallery, Banner, ContactRequest


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "updated")
	readonly_fields = ("updated",)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
	list_display = ("id", "updated")
	readonly_fields = ("updated",)

# Register your models here.

@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
	list_display = ("id", "full_name", "email", "phone", "created", "answered")
	list_filter = ("answered", "created")
	search_fields = ("full_name", "email", "phone", "company")
	readonly_fields = ("created",)
