from django.contrib import admin
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.admin.widgets import AutocompleteSelect
from django import forms
from django.db import models as dj_models
from django.utils.html import mark_safe
from .models import (
    WhiteCategory, WhiteSubcategory, WhiteSubcategoryImage, WhiteSubcategoryPrice,
    WhiteCatalogUser, WhiteCatalogUserActivity,
    WhiteFabricType, WhiteSizeType, WhitePackType,
    WhiteProductVariant, WhiteVariantPackPrice,
    WhiteColor, WhiteColorVariant,
    WhiteCart, WhiteCartItem, WhiteOrder, WhiteOrderItem,
    fill_missing_color_sizes, product_color_sizes,
)


class WhiteSubcategoryInline(admin.TabularInline):
	"""Inline admin for WhiteSubcategory within WhiteCategory."""
	model = WhiteSubcategory
	extra = 1
	fields = ("name", "description", "image", "order", "slug", "is_orderable", "has_order_variants", "has_color_variants")
	prepopulated_fields = {"slug": ("name",)}


class WhiteSubcategoryImageInline(admin.TabularInline):
	model = WhiteSubcategoryImage
	extra = 1
	fields = ("image_preview", "image", "alt_text", "order")
	readonly_fields = ("image_preview",)
	ordering = ("order",)

	def image_preview(self, obj):
		if obj.image:
			return mark_safe(f'<img src="{obj.image.url}" style="max-height: 100px; max-width: 150px;" />')
		return "אין תמונה"
	image_preview.short_description = "תצוגה מקדימה"


class WhiteSubcategoryPriceInline(admin.TabularInline):
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
	list_display = ("name", "show_products_on_homepage", "order", "created", "updated")
	list_editable = ("show_products_on_homepage", "order",)
	list_filter = ("show_products_on_homepage",)
	search_fields = ("name", "description")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")
	inlines = [WhiteSubcategoryInline]
	
	fieldsets = (
		(None, {
			"fields": ("name", "slug", "description", "image", "order", "show_products_on_homepage")
		}),
		("מידע נוסף", {
			"fields": ("created", "updated"),
			"classes": ("collapse",)
		}),
	)


class WhiteProductVariantInline(admin.TabularInline):
	"""Inline: one row = fabric type + size + unit price."""
	model = WhiteProductVariant
	extra = 1
	fields = ("fabric_type", "size_type", "pack_types", "unit_price", "digital_price", "barcode", "is_active", "order")
	show_change_link = True
	formfield_overrides = {
		dj_models.ManyToManyField: {"widget": forms.CheckboxSelectMultiple},
	}


def colors_to_expand(forms):
	"""Colors entered once: a new row, or a row whose size was left empty."""
	color_ids = []
	for inline_form in forms:
		cleaned = getattr(inline_form, "cleaned_data", None)
		if not cleaned or cleaned.get("DELETE"):
			continue
		color = cleaned.get("color")
		if color is None:
			continue
		if inline_form.instance.pk is None or cleaned.get("size") is None:
			color_ids.append(color.pk)
	return color_ids


class ColorAutocompleteSelect(AutocompleteSelect):
	"""Autocomplete whose selected option carries the swatch for the dropdown."""

	def optgroups(self, name, value, attr=None):
		groups = super().optgroups(name, value, attr)
		pks = [
			str(option.get("value"))
			for group in groups
			for option in group[1]
			if option.get("value") not in (None, "")
		]
		colors = {
			str(color.pk): color
			for color in WhiteColor.objects.filter(pk__in=pks)
		}
		for group in groups:
			for option in group[1]:
				color = colors.get(str(option.get("value")))
				if color is None:
					continue
				option["label"] = color.name
				if color.swatch_image:
					option["attrs"]["data-swatch"] = color.swatch_image.url
				elif color.hex_color:
					option["attrs"]["data-hex"] = color.hex_color
		return groups


class SwatchAutocompleteJsonView(AutocompleteJsonView):
	def serialize_result(self, obj, to_field_name):
		payload = super().serialize_result(obj, to_field_name)
		if isinstance(obj, WhiteColor):
			payload["text"] = obj.name
			if obj.swatch_image:
				payload["swatch"] = obj.swatch_image.url
			elif obj.hex_color:
				payload["hex"] = obj.hex_color
		return payload


def _swatch_autocomplete_view(request):
	return SwatchAutocompleteJsonView.as_view(admin_site=admin.site)(request)


admin.site.autocomplete_view = _swatch_autocomplete_view


class WhiteColorVariantInline(admin.TabularInline):
	"""Inline: one new color row is copied onto every size of this product."""
	model = WhiteColorVariant
	extra = 1
	fields = ("color", "size", "barcode", "unit_price", "image", "is_active", "order")
	autocomplete_fields = ("color", "size")
	show_change_link = True

	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		if db_field.name == "color":
			kwargs["widget"] = ColorAutocompleteSelect(
				db_field, self.admin_site, using=kwargs.get("using")
			)
		form_field = super().formfield_for_foreignkey(db_field, request, **kwargs)
		if db_field.name == "color" and form_field is not None:
			form_field.label_from_instance = lambda obj: obj.name
		return form_field

	def get_formset(self, request, obj=None, **kwargs):
		formset = super().get_formset(request, obj, **kwargs)
		sizes = product_color_sizes(obj)
		size_field = formset.form.base_fields.get("size")
		if size_field is not None:
			if sizes:
				names = ", ".join(size.name for size in sizes)
				size_field.label = f"מידה (ריק = {names})"
			else:
				size_field.label = "מידה"
				size_field.help_text = "ריק — שורה אחת לצבע"
		return formset


@admin.register(WhiteSubcategory)
class WhiteSubcategoryAdmin(admin.ModelAdmin):
	"""Admin interface for WhiteSubcategory model."""
	list_display = ("name", "category", "is_orderable", "has_order_variants", "has_color_variants", "unit_price", "online_price", "order", "created", "updated")
	list_editable = ("order",)
	list_filter = ("category", "is_orderable", "has_order_variants", "has_color_variants")
	search_fields = ("name", "description", "category__name")
	prepopulated_fields = {"slug": ("name",)}
	readonly_fields = ("created", "updated")

	class Media:
		js = (
			'https://cdn.tiny.cloud/1/w5lgvxlmv9pmgod7jvot3fppp8plvel9074nteezuwx81znf/tinymce/6/tinymce.min.js',
			'admin_tinymce_init.js',
			'white_catalog/admin_product_color_sample.js',
			'white_catalog/admin_color_autocomplete.js',
		)
		css = {
			'all': (
				'https://cdn.tiny.cloud/1/w5lgvxlmv9pmgod7jvot3fppp8plvel9074nteezuwx81znf/tinymce/6/skins/ui/oxide/skin.rtl.min.css',
				'white_catalog/admin_color_picker.css',
			)
		}
	
	inlines = [WhiteSubcategoryPriceInline, WhiteSubcategoryImageInline, WhiteProductVariantInline, WhiteColorVariantInline]

	def save_formset(self, request, form, formset, change):
		color_ids = colors_to_expand(formset.forms) if formset.model is WhiteColorVariant else []
		super().save_formset(request, form, formset, change)
		if color_ids:
			fill_missing_color_sizes(form.instance, color_ids)

	fieldsets = (
		(None, {
			"fields": ("category", "name", "slug", "description", "image", "order", "is_orderable", "has_order_variants", "has_color_variants")
		}),
		("מחירים", {
			"fields": ("unit_price", "simple_price_label", "online_price"),
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
		fields = (
			'company_name', 'contact_name', 'contact_phone', 'username',
			'pack_route', 'price_percent', 'is_active',
			'hidden_categories', 'hidden_products',
		)
	
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
			self.save_m2m()
		return user


@admin.register(WhiteCatalogUser)
class WhiteCatalogUserAdmin(admin.ModelAdmin):
	"""Admin interface for WhiteCatalogUser model."""
	form = WhiteCatalogUserForm
	list_display = ("company_name", "username", "contact_name", "contact_phone", "pack_route", "price_percent", "is_active", "last_login_display", "last_activity_display", "created")
	list_editable = ("price_percent", "is_active")
	list_filter = ("pack_route", "price_percent", "is_active", "created", "last_login", "last_activity_at")
	search_fields = ("company_name", "username", "contact_name", "contact_phone")
	readonly_fields = ("created", "updated", "last_login", "last_activity_at", "activity_count")
	filter_horizontal = ("hidden_categories", "hidden_products")
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
		("מסלול מוצרים", {
			"fields": ("pack_route",),
			"description": "ביגוד מוזמן בשלישיות בלבד. חמישיות לא בשימוש."
		}),
		("מחיר", {
			"fields": ("price_percent",),
			"description": "אחוז הנחה ממחיר הקטלוג. 0 = מחיר מלא. 10 = 10% הנחה (13 ₪ הופך ל־11.7). המחיר אחרי הנחה מעוגל לעשירית השקל.",
		}),
		("התאמת קטלוג", {
			"fields": ("hidden_categories", "hidden_products"),
			"description": "ברירת מחדל: הכל גלוי כמו בקטלוג. סמן כאן רק מה להסתיר אצל המשתמש הזה. הסתרת קטגוריה מסתירה גם את כל המוצרים שלה.",
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

@admin.register(WhiteFabricType)
class WhiteFabricTypeAdmin(admin.ModelAdmin):
	list_display = ("name", "description", "is_active", "order")
	list_editable = ("is_active", "order")
	search_fields = ("name", "description")


@admin.register(WhiteSizeType)
class WhiteSizeTypeAdmin(admin.ModelAdmin):
	list_display = ("name", "order", "is_active")
	list_editable = ("order", "is_active")
	search_fields = ("name",)


@admin.register(WhitePackType)
class WhitePackTypeAdmin(admin.ModelAdmin):
	list_display = ("name", "quantity", "order", "is_active")
	list_editable = ("order", "is_active")
	search_fields = ("name",)


@admin.register(WhiteColor)
class WhiteColorAdmin(admin.ModelAdmin):
	list_display = ("swatch_preview", "name", "notes", "hex_color", "order", "is_active")
	list_display_links = ("name",)
	list_editable = ("notes", "hex_color", "order", "is_active")
	search_fields = ("name", "notes", "hex_color")
	list_filter = ("is_active",)
	ordering = ("order", "name")

	class Media:
		js = ("white_catalog/admin_color_picker.js",)
		css = {"all": ("white_catalog/admin_color_picker.css",)}

	fieldsets = (
		(None, {
			"fields": ("name", "notes", "hex_color", "swatch_image", "order", "is_active"),
			"description": (
				"אחרי בחירת תמונת דוגמית, «ערוך תמונת דוגמית» מציג עיגול באותו גודל שהלקוח רואה. "
				"גוררים את התמונה מתחת לעיגול ומגדילים בגלגלת. מה שבתוך העיגול נשמר כדוגמית. "
				"לחיצה על נקודה דוגמת רק את קוד הצבע, בלי להחליף את התמונה."
			),
		}),
	)

	def swatch_preview(self, obj):
		if obj.swatch_image:
			return mark_safe(
				f'<img src="{obj.swatch_image.url}" style="width:28px;height:28px;border-radius:50%;'
				f'object-fit:cover;border:1px solid #ccc;" />'
			)
		if obj.hex_color:
			return mark_safe(
				f'<span style="display:inline-block;width:28px;height:28px;border-radius:50%;'
				f'background:{obj.hex_color};border:1px solid #ccc;"></span>'
			)
		return "-"
	swatch_preview.short_description = "דוגמית"


@admin.register(WhiteColorVariant)
class WhiteColorVariantAdmin(admin.ModelAdmin):
	list_display = ("product", "color", "size", "barcode", "unit_price", "is_active", "order")
	list_editable = ("barcode", "unit_price", "is_active", "order")
	list_filter = ("color", "size", "product", "is_active")
	search_fields = ("color__name", "color__notes", "size__name", "product__name", "barcode")
	autocomplete_fields = ("product", "color", "size")
	ordering = ("product__name", "order", "color__order")
	list_per_page = 200

	class Media:
		js = ("white_catalog/admin_color_autocomplete.js",)
		css = {"all": ("white_catalog/admin_color_picker.css",)}

	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		if db_field.name == "color":
			kwargs["widget"] = ColorAutocompleteSelect(
				db_field, self.admin_site, using=kwargs.get("using")
			)
		form_field = super().formfield_for_foreignkey(db_field, request, **kwargs)
		if db_field.name == "color" and form_field is not None:
			form_field.label_from_instance = lambda obj: obj.name
		return form_field

	def save_model(self, request, obj, form, change):
		super().save_model(request, obj, form, change)
		if not change or obj.size_id is None:
			fill_missing_color_sizes(obj.product, [obj.color_id])


class WhiteVariantPackPriceInline(admin.TabularInline):
	model = WhiteVariantPackPrice
	extra = 1
	fields = ("pack_type", "price")


@admin.register(WhiteProductVariant)
class WhiteProductVariantAdmin(admin.ModelAdmin):
	list_display = ("product", "fabric_type", "size_type", "unit_price", "digital_price", "barcode", "is_active", "order")
	list_editable = ("unit_price", "digital_price", "barcode", "is_active", "order")
	list_filter = ("fabric_type", "product", "pack_types", "is_active")
	search_fields = ("fabric_type__name", "size_type__name", "product__name", "barcode")
	ordering = ("product__name", "fabric_type__name", "size_type__order")
	list_per_page = 200
	actions = ("export_variants_csv",)
	formfield_overrides = {
		dj_models.ManyToManyField: {"widget": forms.CheckboxSelectMultiple},
	}

	@admin.action(description="ייצוא ל-CSV")
	def export_variants_csv(self, request, queryset):
		import csv
		from django.http import HttpResponse

		queryset = queryset.select_related("product", "fabric_type", "size_type").prefetch_related("pack_types")

		response = HttpResponse(content_type="text/csv; charset=utf-8")
		response["Content-Disposition"] = "attachment; filename=variants.csv"
		response.write("\ufeff")  # BOM so Excel reads Hebrew correctly

		writer = csv.writer(response)
		writer.writerow(["מוצר", "סוג בד", "מידה", "צורת אריזה", "מחיר ליחידה", "ברקוד", "פעיל"])
		for variant in queryset:
			pack_names = ", ".join(pt.name for pt in variant.pack_types.all())
			writer.writerow([
				variant.product.name,
				variant.fabric_type.name,
				variant.size_type.name,
				pack_names,
				variant.unit_price if variant.unit_price is not None else "",
				variant.barcode,
				"כן" if variant.is_active else "לא",
			])
		return response




class WhiteCartItemInline(admin.TabularInline):
	model = WhiteCartItem
	extra = 0
	readonly_fields = ("product", "variant", "color_variant", "pack_type", "quantity", "price_at_add", "get_line_total")
	fields = ("product", "variant", "color_variant", "pack_type", "quantity", "price_at_add", "get_line_total")
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
	readonly_fields = ("product_name", "variant_name", "color_name", "barcode", "size_name", "pack_type_name", "pack_quantity", "quantity", "unit_price", "get_line_total")
	fields = ("product_name", "variant_name", "color_name", "barcode", "size_name", "pack_type_name", "pack_quantity", "quantity", "unit_price", "get_line_total")
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

