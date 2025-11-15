from django.contrib import admin
from django import forms
from .models import WhiteCategory, WhiteSubcategory, WhiteSubcategoryImage, WhiteCatalogUser


class WhiteSubcategoryInline(admin.TabularInline):
	"""Inline admin for WhiteSubcategory within WhiteCategory."""
	model = WhiteSubcategory
	extra = 1
	fields = ("name", "description", "image", "order", "slug")
	prepopulated_fields = {"slug": ("name",)}


class WhiteSubcategoryImageInline(admin.TabularInline):
	"""Inline admin for WhiteSubcategoryImage within WhiteSubcategory."""
	model = WhiteSubcategoryImage
	extra = 1
	fields = ("image", "alt_text", "order")
	ordering = ("order",)


@admin.register(WhiteCategory)
class WhiteCategoryAdmin(admin.ModelAdmin):
	"""Admin interface for WhiteCategory model."""
	list_display = ("name", "order", "created", "updated")
	list_editable = ("order",)
	search_fields = ("name", "description")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")
	inlines = [WhiteSubcategoryInline]
	
	fieldsets = (
		(None, {
			"fields": ("name", "slug", "description", "image", "order")
		}),
		("מידע נוסף", {
			"fields": ("created", "updated"),
			"classes": ("collapse",)
		}),
	)


@admin.register(WhiteSubcategory)
class WhiteSubcategoryAdmin(admin.ModelAdmin):
	"""Admin interface for WhiteSubcategory model."""
	list_display = ("name", "category", "order", "created", "updated")
	list_editable = ("order",)
	list_filter = ("category",)
	search_fields = ("name", "description", "category__name")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")
	inlines = [WhiteSubcategoryImageInline]
	
	class Media:
		js = (
			'https://cdn.tiny.cloud/1/w5lgvxlmv9pmgod7jvot3fppp8plvel9074nteezuwx81znf/tinymce/6/tinymce.min.js',
			'admin_tinymce_init.js',
		)
		css = {
			'all': ('https://cdn.tiny.cloud/1/w5lgvxlmv9pmgod7jvot3fppp8plvel9074nteezuwx81znf/tinymce/6/skins/ui/oxide/skin.rtl.min.css',)
		}
	
	fieldsets = (
		(None, {
			"fields": ("category", "name", "slug", "description", "image", "order")
		}),
		("פרטים נוספים", {
			"fields": ("marketing_description", "information", "pattern_and_branding", "fabric_production", "sizes"),
			"classes": ("wide",)
		}),
		("מידע נוסף", {
			"fields": ("created", "updated"),
			"classes": ("collapse",)
		}),
	)



class WhiteCatalogUserForm(forms.ModelForm):
	"""Custom form for WhiteCatalogUser with password handling."""
	password = forms.CharField(
		label="סיסמא",
		widget=forms.PasswordInput(attrs={'placeholder': 'הכנס סיסמא חדשה'}),
		required=False,
		help_text="השאר ריק כדי לשמור על הסיסמא הקיימת"
	)
	
	class Meta:
		model = WhiteCatalogUser
		fields = ('company_name', 'contact_name', 'contact_phone', 'username', 'is_active')
	
	def save(self, commit=True):
		user = super().save(commit=False)
		password = self.cleaned_data.get('password')
		if password:
			user.set_password(password)
		elif not user.pk:
			# New user without password - set a random one
			from django.utils.crypto import get_random_string
			user.set_password(get_random_string(12))
		if commit:
			user.save()
		return user


@admin.register(WhiteCatalogUser)
class WhiteCatalogUserAdmin(admin.ModelAdmin):
	"""Admin interface for WhiteCatalogUser model."""
	form = WhiteCatalogUserForm
	list_display = ("company_name", "username", "contact_name", "contact_phone", "is_active", "created")
	list_editable = ("is_active",)
	list_filter = ("is_active", "created")
	search_fields = ("company_name", "username", "contact_name", "contact_phone")
	readonly_fields = ("created", "updated")
	
	fieldsets = (
		("פרטי עסק", {
			"fields": ("company_name", "contact_name", "contact_phone")
		}),
		("פרטי התחברות", {
			"fields": ("username", "password", "is_active")
		}),
		("מידע נוסף", {
			"fields": ("created", "updated"),
			"classes": ("collapse",)
		}),
	)

