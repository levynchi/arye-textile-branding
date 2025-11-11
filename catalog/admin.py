from django.contrib import admin
from django import forms
from .models import Category, Subcategory, SubcategoryImage, CatalogUser


class SubcategoryAdminForm(forms.ModelForm):
	"""Custom form for Subcategory with larger textareas for HTML fields."""
	class Meta:
		model = Subcategory
		fields = '__all__'
		widgets = {
			'marketing_description': forms.Textarea(attrs={'rows': 10, 'cols': 80, 'style': 'font-family: monospace;'}),
			'information': forms.Textarea(attrs={'rows': 10, 'cols': 80, 'style': 'font-family: monospace;'}),
			'pattern_and_branding': forms.Textarea(attrs={'rows': 10, 'cols': 80, 'style': 'font-family: monospace;'}),
			'fabric_production': forms.Textarea(attrs={'rows': 10, 'cols': 80, 'style': 'font-family: monospace;'}),
			'sizes': forms.Textarea(attrs={'rows': 10, 'cols': 80, 'style': 'font-family: monospace;'}),
		}


class SubcategoryInline(admin.TabularInline):
	"""Inline admin for Subcategory within Category."""
	model = Subcategory
	extra = 1
	fields = ("name", "description", "image", "order", "slug")
	prepopulated_fields = {"slug": ("name",)}


class SubcategoryImageInline(admin.TabularInline):
	"""Inline admin for SubcategoryImage within Subcategory."""
	model = SubcategoryImage
	extra = 1
	fields = ("image", "alt_text", "order")
	ordering = ("order",)


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
	form = SubcategoryAdminForm
	list_display = ("name", "category", "order", "created", "updated")
	list_editable = ("order",)
	list_filter = ("category",)
	search_fields = ("name", "description", "category__name")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")
	inlines = [SubcategoryImageInline]
	
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



class CatalogUserForm(forms.ModelForm):
	"""Custom form for CatalogUser with password handling."""
	password = forms.CharField(
		label="סיסמא",
		widget=forms.PasswordInput(attrs={'placeholder': 'הכנס סיסמא חדשה'}),
		required=False,
		help_text="השאר ריק כדי לשמור על הסיסמא הקיימת"
	)
	
	class Meta:
		model = CatalogUser
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


@admin.register(CatalogUser)
class CatalogUserAdmin(admin.ModelAdmin):
	"""Admin interface for CatalogUser model."""
	form = CatalogUserForm
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
