from django.contrib import admin
from .models import Gallery, Banner


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "updated")
	readonly_fields = ("updated",)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
	list_display = ("id", "updated")
	readonly_fields = ("updated",)

# Register your models here.
