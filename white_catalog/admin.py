from django.contrib import admin
from django import forms
from django.utils.html import mark_safe
from .models import (
    WhiteCategory, WhiteSubcategory, WhiteSubcategoryImage, WhiteSubcategoryPrice,
    WhiteCatalogUser, WhiteCatalogUserActivity,
    WhitePackType, WhiteProductVariant, WhiteVariantSize, WhiteVariantPackPrice,
    WhiteCart, WhiteCartItem, WhiteOrder, WhiteOrderItem,
)


class WhiteSubcategoryInline(admin.TabularInline):
	"""Inline admin for WhiteSubcategory within WhiteCategory."""
	model = WhiteSubcategory
	extra = 1
	fields = ("name", "description", "image", "order", "slug", "is_orderable")
	prepopulated_fields = {"slug": ("name",)}


class WhiteSubcategoryImageInline(admin.TabularInline):
	"""Inline admin for WhiteSubcategoryImage within WhiteSubcategory."""
	model = WhiteSubcategoryImage
	extra = 1
	fields = ("image_preview", "image", "alt_text", "order")
	readonly_fields = ("image_preview",)
	ordering = ("order",)
	
	def image_preview(self, obj):
		"""Display a thumbnail preview of the image."""
		if obj.image:
			return mark_safe(f'<img src="{obj.image.url}" style="max-height: 100px; max-width: 150px;" />')
		return "אין תמונה"
	image_preview.short_description = "תצוגה מקדימה"


class WhiteSubcategoryPriceInline(admin.TabularInline):
	"""Inline admin for WhiteSubcategoryPrice within WhiteSubcategory."""
	model = WhiteSubcategoryPrice
	extra = 1
	fields = ("size_name", "price", "order")
	ordering = ("order",)


class WhiteCatalogUserActivityInline(admin.TabularInline):
	"""Inline admin for WhiteCatalogUserActivity within WhiteCatalogUser."""
	model = WhiteCatalogUserActivity
	extra = 0
	max_num = 10
	can_delete = False
	fields = ("timestamp", "ip_address", "user_agent_short", "page_url")
	readonly_fields = ("timestamp", "ip_address", "user_agent_short", "page_url")
	ordering = ("-timestamp",)
	
	def user_agent_short(self, obj):
		"""Display a shortened version of the user agent."""
		if obj.user_agent and len(obj.user_agent) > 60:
			return obj.user_agent[:60] + "..."
		return obj.user_agent or "-"
	user_agent_short.short_description = "דפדפן"
	
	def has_add_permission(self, request, obj=None):
		return False


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


class WhiteProductVariantInline(admin.TabularInline):
	"""Inline admin for WhiteProductVariant within WhiteSubcategory."""
	model = WhiteProductVariant
	extra = 1
	fields = ("name", "description", "is_active", "order")
	show_change_link = True


@admin.register(WhiteSubcategory)
class WhiteSubcategoryAdmin(admin.ModelAdmin):
	"""Admin interface for WhiteSubcategory model."""
	list_display = ("name", "category", "unit_price", "online_price", "order", "created", "updated")
	list_editable = ("order",)
	list_filter = ("category",)
	search_fields = ("name", "description", "category__name")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")

	class Media:
		js = (
			'https://cdn.tiny.cloud/1/w5lgvxlmv9pmgod7jvot3fppp8plvel9074nteezuwx81znf/tinymce/6/tinymce.min.js',
			'admin_tinymce_init.js',
		)
		css = {
			'all': ('https://cdn.tiny.cloud/1/w5lgvxlmv9pmgod7jvot3fppp8plvel9074nteezuwx81znf/tinymce/6/skins/ui/oxide/skin.rtl.min.css',)
		}
	
	inlines = [WhiteSubcategoryPriceInline, WhiteSubcategoryImageInline, WhiteProductVariantInline]

	fieldsets = (
		(None, {
			"fields": ("category", "name", "slug", "description", "image", "order", "is_orderable")
		}),
		("מחירים (למוצרים ללא גרסאות)", {
			"fields": ("unit_price", "online_price"),
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
	list_display = ("company_name", "username", "contact_name", "contact_phone", "is_active", "last_login_display", "last_activity_display", "created")
	list_editable = ("is_active",)
	list_filter = ("is_active", "created", "last_login", "last_activity_at")
	search_fields = ("company_name", "username", "contact_name", "contact_phone")
	readonly_fields = ("created", "updated", "last_login", "last_activity_at", "activity_count")
	inlines = [WhiteCatalogUserActivityInline]
	
	def last_login_display(self, obj):
		"""Display last login time in a user-friendly format."""
		if obj.last_login:
			return obj.last_login.strftime("%d/%m/%Y %H:%M")
		return "-"
	last_login_display.short_description = "כניסה אחרונה"
	last_login_display.admin_order_field = "last_login"
	
	def last_activity_display(self, obj):
		"""Display last activity time in a user-friendly format."""
		if obj.last_activity_at:
			return obj.last_activity_at.strftime("%d/%m/%Y %H:%M")
		return "-"
	last_activity_display.short_description = "פעילות אחרונה"
	last_activity_display.admin_order_field = "last_activity_at"
	
	def activity_count(self, obj):
		"""Display total number of activities."""
		if obj.pk:
			count = obj.activities.count()
			return f"{count} פעילויות"
		return "-"
	activity_count.short_description = "סה\"כ פעילויות"
	
	fieldsets = (
		("פרטי עסק", {
			"fields": ("company_name", "contact_name", "contact_phone")
		}),
		("פרטי התחברות", {
			"fields": ("username", "password", "is_active")
		}),
		("פעילות", {
			"fields": ("last_login", "last_activity_at", "activity_count"),
			"classes": ("wide",)
		}),
		("מידע נוסף", {
			"fields": ("created", "updated"),
			"classes": ("collapse",)
		}),
	)


@admin.register(WhiteCatalogUserActivity)
class WhiteCatalogUserActivityAdmin(admin.ModelAdmin):
	"""Admin interface for WhiteCatalogUserActivity model."""
	list_display = ("user", "timestamp", "ip_address", "page_url_short", "user_agent_short")
	list_filter = ("timestamp", "user")
	search_fields = ("user__username", "user__company_name", "ip_address", "page_url")
	readonly_fields = ("user", "timestamp", "ip_address", "user_agent", "page_url")
	date_hierarchy = "timestamp"
	
	def page_url_short(self, obj):
		"""Display a shortened version of the page URL."""
		if obj.page_url and len(obj.page_url) > 50:
			return obj.page_url[:50] + "..."
		return obj.page_url or "-"
	page_url_short.short_description = "דף"
	
	def user_agent_short(self, obj):
		"""Display a shortened version of the user agent."""
		if obj.user_agent and len(obj.user_agent) > 50:
			return obj.user_agent[:50] + "..."
		return obj.user_agent or "-"
	user_agent_short.short_description = "דפדפן"
	
	def has_add_permission(self, request):
		"""Prevent manual addition of activity logs."""
		return False

	def has_change_permission(self, request, obj=None):
		"""Prevent editing of activity logs."""
		return False


# ---------------------------------------------------------------------------
# Ordering system admin
# ---------------------------------------------------------------------------

@admin.register(WhitePackType)
class WhitePackTypeAdmin(admin.ModelAdmin):
	list_display = ("name", "quantity", "order", "is_active")
	list_editable = ("order", "is_active")
	search_fields = ("name",)


class WhiteVariantPackPriceInline(admin.TabularInline):
	model = WhiteVariantPackPrice
	extra = 1
	fields = ("pack_type", "price")


class WhiteVariantSizeInline(admin.TabularInline):
	model = WhiteVariantSize
	extra = 1
	fields = ("size_name", "order")


@admin.register(WhiteProductVariant)
class WhiteProductVariantAdmin(admin.ModelAdmin):
	list_display = ("product", "name", "is_active", "order")
	list_editable = ("is_active", "order")
	list_filter = ("product", "is_active")
	search_fields = ("name", "product__name")
	inlines = [WhiteVariantSizeInline]


@admin.register(WhiteVariantSize)
class WhiteVariantSizeAdmin(admin.ModelAdmin):
	list_display = ("variant", "size_name", "order")
	list_editable = ("order",)
	list_filter = ("variant__product",)
	search_fields = ("size_name", "variant__name", "variant__product__name")
	inlines = [WhiteVariantPackPriceInline]


class WhiteCartItemInline(admin.TabularInline):
	model = WhiteCartItem
	extra = 0
	readonly_fields = ("product", "variant", "variant_size", "pack_type", "quantity", "price_at_add", "get_line_total")
	fields = ("product", "variant", "variant_size", "pack_type", "quantity", "price_at_add", "get_line_total")
	can_delete = False

	def get_line_total(self, obj):
		return f"₪{obj.get_line_total()}"
	get_line_total.short_description = "סה\"כ"

	def has_add_permission(self, request, obj=None):
		return False


@admin.register(WhiteCart)
class WhiteCartAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "status", "get_item_count", "get_total", "created", "updated")
	list_filter = ("status", "created")
	search_fields = ("user__company_name", "user__username")
	readonly_fields = ("user", "status", "created", "updated")
	inlines = [WhiteCartItemInline]

	def get_total(self, obj):
		return f"₪{obj.get_total()}"
	get_total.short_description = "סה\"כ"

	def has_add_permission(self, request):
		return False


class WhiteOrderItemInline(admin.TabularInline):
	model = WhiteOrderItem
	extra = 0
	readonly_fields = ("product_name", "variant_name", "size_name", "pack_type_name", "pack_quantity", "quantity", "unit_price", "get_line_total")
	fields = ("product_name", "variant_name", "size_name", "pack_type_name", "pack_quantity", "quantity", "unit_price", "get_line_total")
	can_delete = False

	def get_line_total(self, obj):
		return f"₪{obj.get_line_total()}"
	get_line_total.short_description = "סה\"כ"

	def has_add_permission(self, request, obj=None):
		return False


@admin.register(WhiteOrder)
class WhiteOrderAdmin(admin.ModelAdmin):
	list_display = ("order_number", "user", "status", "total_amount", "created", "updated")
	list_filter = ("status", "created")
	search_fields = ("order_number", "user__company_name", "user__username")
	readonly_fields = ("order_number", "user", "cart", "total_amount", "created", "updated")
	inlines = [WhiteOrderItemInline]

	fieldsets = (
		("פרטי הזמנה", {
			"fields": ("order_number", "user", "status", "total_amount", "created", "updated")
		}),
		("הערות", {
			"fields": ("notes", "admin_notes"),
		}),
	)

