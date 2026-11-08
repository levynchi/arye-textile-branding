from decimal import Decimal

from django.contrib import admin
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.admin.widgets import AutocompleteSelect
from django import forms
from django.contrib import messages
from django.db import models as dj_models
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe
from .models import (
    WhiteCategory, WhiteSubcategory, WhiteSubcategoryImage, WhiteSubcategoryPrice,
    WhiteCatalogUser, WhiteCatalogUserActivity,
    WhiteFabricType, WhiteSizeType, WhitePackType,
    WhiteProductVariant, WhiteVariantPackPrice,
    WhiteColor, WhiteColorVariant,
    WhiteCart, WhiteCartItem, WhiteOrder, WhiteOrderItem, WhiteQuote,
    apply_price_list, fill_missing_color_sizes, product_color_sizes,
)
from .rivhit import (
    RivhitApiError, cached_customers, cached_item_ids_by_barcode, create_quote_document,
    customer_display, get_rivhit_client, match_customers, quote_line_description, rivhit_token,
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
			"fields": ("category", "name", "slug", "description", "image", "order", "is_orderable", "has_order_variants", "has_color_variants", "sizes_share_quantity")
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
			'pack_route', 'price_percent', 'is_active', 'rivhit_customer_id',
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


def whatsapp_phone(raw_phone):
	"""Israeli phone as typed by staff -> international digits for wa.me (05X... -> 9725X...)."""
	digits = "".join(ch for ch in (raw_phone or "") if ch.isdigit())
	if not digits:
		return ""
	if digits.startswith("00"):
		digits = digits[2:]
	if digits.startswith("0"):
		digits = "972" + digits[1:]
	return digits


def customer_order_message(user, login_url):
	"""WhatsApp text inviting the customer to review the order staff prepared for them."""
	first_name = (user.contact_name or "").strip().split(" ")[0] or user.company_name
	return (
		f"היי {first_name},\n"
		f"הכנו עבורכם ({user.company_name}) הצעה להזמנה בקטלוג הלבנים של אריה טקסטיל.\n"
		f"כנסו לקטלוג עם שם המשתמש: {user.username}\n"
		f"{login_url}\n"
		"בדף ההזמנה תראו את המוצרים והכמויות שהכנו. אפשר לשנות כמויות, להוסיף או להוריד מוצרים, "
		"וכשהכל מתאים - ללחוץ על \"שלח הזמנה\".\n"
		"לכל שאלה אנחנו כאן."
	)


def whatsapp_link(user, login_url):
	phone = whatsapp_phone(user.contact_phone)
	if not phone:
		return ""
	from urllib.parse import quote
	return f"https://wa.me/{phone}?text={quote(customer_order_message(user, login_url))}"


@admin.register(WhiteCatalogUser)
class WhiteCatalogUserAdmin(admin.ModelAdmin):
	"""Admin interface for WhiteCatalogUser model."""
	form = WhiteCatalogUserForm
	change_form_template = "admin/white_catalog/whitecataloguser_change_form.html"
	list_display = ("company_name", "username", "contact_name", "contact_phone", "pack_route", "price_percent", "is_active", "active_cart_display", "last_login_display", "last_activity_display", "created")
	list_editable = ("price_percent", "is_active")
	list_filter = ("pack_route", "price_percent", "is_active", "created", "last_login", "last_activity_at")
	search_fields = ("company_name", "username", "contact_name", "contact_phone")
	readonly_fields = ("created", "updated", "last_login", "last_activity_at", "activity_count")
	filter_horizontal = ("hidden_categories", "hidden_products")
	inlines = [WhiteCatalogUserActivityInline]

	def active_cart_display(self, obj):
		"""Items waiting in the customer's open order page + a one-click 'enter as customer' button."""
		cart = WhiteCart.objects.filter(user=obj, status=WhiteCart.STATUS_ACTIVE).first()
		count = cart.get_item_count() if cart else 0
		label = f"{count} פריטים" if count else "ריק"
		if not obj.is_active:
			return label
		# The changelist is already one big POST form (list_editable), so the button
		# re-targets that form instead of nesting a second one.
		return format_html(
			'{} &nbsp;<button type="submit" class="button" formmethod="post" formaction="{}" '
			'style="padding:2px 8px;">כניסה כלקוח</button>',
			label,
			reverse("white_catalog:admin_login_as", args=[obj.pk]),
		)
	active_cart_display.short_description = "דף הזמנה פתוח"

	def change_view(self, request, object_id, form_url="", extra_context=None):
		extra_context = dict(extra_context or {})
		user = WhiteCatalogUser.objects.filter(pk=object_id).first()
		if user:
			login_url = request.build_absolute_uri(reverse("white_catalog:login"))
			extra_context["login_as_url"] = reverse("white_catalog:admin_login_as", args=[user.pk])
			extra_context["whatsapp_url"] = whatsapp_link(user, login_url)
			extra_context["whatsapp_message"] = customer_order_message(user, login_url)
			cart = WhiteCart.objects.filter(user=user, status=WhiteCart.STATUS_ACTIVE).first()
			extra_context["active_cart_count"] = cart.get_item_count() if cart else 0
		return super().change_view(request, object_id, form_url, extra_context=extra_context)
	
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


def _pick_pack_type(variant, user):
	"""The pack a staff-added variant row is sold in: the customer's route, else threes."""
	packs = list(variant.pack_types.filter(is_active=True)) or list(WhitePackType.objects.filter(is_active=True))
	if not packs:
		return None
	route = getattr(user, "pack_route", None)
	if route == WhiteCatalogUser.ROUTE_FIVES:
		wanted = 5
	else:
		wanted = 3
	for pack in packs:
		if pack.quantity == wanted:
			return pack
	return packs[0]


def fill_order_item_from_catalog(item, user):
	"""Snapshot catalog data onto a staff-added order line, pricing it like the cart does.

	A price typed by staff wins; otherwise the catalog price after the customer's
	discount is used (pack price when defined, else unit price x pack size).
	"""
	typed_price = item.unit_price
	if item.color_variant_id:
		cv = item.color_variant
		item.product = cv.product
		item.variant = None
		item.product_name = cv.product.name
		item.variant_name = "מניפת צבעים"
		item.color_name = cv.color.name
		item.barcode = cv.barcode or ""
		item.size_name = f"{cv.color.name} · {cv.size.name}" if cv.size_id else cv.color.name
		item.pack_type_name = "יחידה"
		item.pack_quantity = 1
		if typed_price is None:
			item.unit_price = apply_price_list(cv.get_effective_price(), user)
	elif item.variant_id:
		variant = item.variant
		item.product = variant.product
		item.color_variant = None
		item.product_name = variant.product.name
		item.variant_name = variant.name
		item.color_name = ""
		item.barcode = variant.barcode or ""
		item.size_name = variant.size_type.name if variant.size_type_id else ""
		pack = _pick_pack_type(variant, user)
		item.pack_type_name = pack.name if pack else "יחידה"
		item.pack_quantity = pack.quantity if pack else 1
		if typed_price is None:
			pack_price = None
			if pack is not None:
				pack_price = variant.pack_prices.filter(pack_type=pack).values_list("price", flat=True).first()
			if pack_price is not None:
				item.unit_price = apply_price_list(pack_price, user)
			else:
				unit = variant.unit_price if variant.unit_price is not None else variant.product.unit_price
				effective = apply_price_list(unit, user)
				item.unit_price = (effective or Decimal("0")) * item.pack_quantity
	if item.unit_price is None:
		item.unit_price = Decimal("0")
	return item


def recalc_order_total(order):
	total = sum((line.get_line_total() for line in order.items.all()), Decimal("0"))
	order.total_amount = total
	WhiteOrder.objects.filter(pk=order.pk).update(total_amount=total)
	return total


class WhiteOrderItemForm(forms.ModelForm):
	class Meta:
		model = WhiteOrderItem
		fields = ("variant", "color_variant", "quantity", "unit_price")

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields["unit_price"].required = False
		self.fields["unit_price"].help_text = "ריק = מחיר הקטלוג אחרי ההנחה של הלקוח"
		if self.instance.pk:
			# Existing lines are snapshots: the catalog pickers only matter for new rows.
			for name in ("variant", "color_variant"):
				if name in self.fields:
					self.fields[name].disabled = True
					self.fields[name].required = False

	def clean(self):
		cleaned = super().clean()
		quantity = cleaned.get("quantity")
		if quantity is not None and quantity < 1 and not cleaned.get("DELETE"):
			self.add_error("quantity", "כמות חייבת להיות לפחות 1. למחיקה סמן את תיבת המחיקה.")
		if self.instance.pk:
			return cleaned
		if not cleaned.get("variant") and not cleaned.get("color_variant"):
			if cleaned.get("quantity") or cleaned.get("unit_price") is not None:
				raise forms.ValidationError("בשורה חדשה צריך לבחור גרסה (מוצר + בד + מידה) או צבע מהמניפה.")
		if cleaned.get("variant") and cleaned.get("color_variant"):
			raise forms.ValidationError("בחר גרסה או צבע, לא את שניהם.")
		return cleaned

	def has_changed(self):
		# An untouched extra row must stay empty so the formset skips it.
		if self.instance.pk:
			return super().has_changed()
		return bool(self.data.get(self.add_prefix("variant")) or self.data.get(self.add_prefix("color_variant")))


class WhiteOrderItemInline(admin.TabularInline):
	model = WhiteOrderItem
	form = WhiteOrderItemForm
	extra = 1
	fields = ("variant", "color_variant", "product_name", "variant_name", "color_name", "barcode", "size_name", "pack_type_name", "pack_quantity", "quantity", "unit_price", "get_line_total")
	readonly_fields = ("product_name", "variant_name", "color_name", "barcode", "size_name", "pack_type_name", "pack_quantity", "get_line_total")
	autocomplete_fields = ("variant", "color_variant")
	can_delete = True
	verbose_name = "פריט"
	verbose_name_plural = "פריטי הזמנה — אפשר לשנות כמות ומחיר, למחוק, או להוסיף שורה (בחר גרסה או צבע; המחיר והפרטים יתמלאו לבד בשמירה)"

	def get_line_total(self, obj):
		if not obj.pk or obj.unit_price is None:
			return "—"
		return f"₪{obj.get_line_total()}"
	get_line_total.short_description = "סה\"כ"

	def formfield_for_foreignkey(self, db_field, request, **kwargs):
		form_field = super().formfield_for_foreignkey(db_field, request, **kwargs)
		if form_field is not None and db_field.name == "variant":
			form_field.label = "גרסה (מוצר + בד + מידה)"
			form_field.label_from_instance = lambda obj: f"{obj.product.name} — {obj.name}"
		if form_field is not None and db_field.name == "color_variant":
			form_field.label = "צבע מהמניפה"
		return form_field


@admin.register(WhiteOrder)
class WhiteOrderAdmin(admin.ModelAdmin):
	list_display = ("order_number", "user", "status", "total_amount", "created", "updated")
	list_filter = ("status", "created")
	search_fields = ("order_number", "user__company_name", "user__username")
	readonly_fields = ("order_number", "user", "cart", "total_amount", "created", "updated", "quotes_display")
	inlines = [WhiteOrderItemInline]
	change_form_template = "admin/white_catalog/whiteorder_change_form.html"

	fieldsets = (
		("פרטי הזמנה", {
			"fields": ("order_number", "user", "status", "total_amount", "created", "updated"),
			"description": "סה\"כ מחושב מחדש מהפריטים בכל שמירה.",
		}),
		("הערות", {
			"fields": ("notes", "admin_notes"),
		}),
		("הצעות מחיר בריווחית", {
			"fields": ("quotes_display",),
			"description": "להפקת הצעה חדשה: כפתור «הצעת מחיר בריווחית» למעלה.",
		}),
	)

	def quotes_display(self, obj):
		if not obj or not obj.pk:
			return "—"
		quotes = list(obj.quotes.all())
		if not quotes:
			return "עדיין לא הופקה הצעת מחיר מהזמנה זו."
		rows = []
		for quote in quotes:
			link = (
				format_html(' — <a href="{}" target="_blank" rel="noopener">פתח PDF</a>', quote.rivhit_document_link)
				if quote.rivhit_document_link else ""
			)
			rows.append(format_html(
				"<li>{} — הצעה {} — לקוח #{}{}</li>",
				quote.created.strftime("%d/%m/%Y %H:%M"),
				quote.rivhit_document_number or "—",
				quote.rivhit_customer_id or "—",
				link,
			))
		return format_html("<ul style='margin:0;padding-inline-start:1.2em'>{}</ul>", mark_safe("".join(rows)))
	quotes_display.short_description = "הצעות שהופקו"

	def save_formset(self, request, form, formset, change):
		if formset.model is not WhiteOrderItem:
			return super().save_formset(request, form, formset, change)
		order = form.instance
		instances = formset.save(commit=False)
		for obj in formset.deleted_objects:
			obj.delete()
		for item in instances:
			item.order = order
			if item.pk is None or not item.product_name:
				fill_order_item_from_catalog(item, order.user)
			elif item.unit_price is None:
				item.unit_price = Decimal("0")
			item.save()
		formset.save_m2m()
		recalc_order_total(order)

	def get_urls(self):
		urls = super().get_urls()
		custom = [
			path(
				"<int:object_id>/print/",
				self.admin_site.admin_view(self.print_order),
				name="white_catalog_whiteorder_print",
			),
			path(
				"<int:object_id>/quote/",
				self.admin_site.admin_view(self.quote_order),
				name="white_catalog_whiteorder_quote",
			),
		]
		return custom + urls

	# ------------------------------------------------------------------ Rivhit quote
	@staticmethod
	def _quote_rows(items, qty_map=None):
		rows = []
		qty_total = 0
		amount_total = Decimal("0")
		for item in items:
			qty = item.quantity if qty_map is None else qty_map.get(item.pk, item.quantity)
			price = item.unit_price if item.unit_price is not None else Decimal("0")
			line_total = price * qty
			qty_total += qty
			amount_total += line_total
			rows.append({
				"item": item,
				"description": quote_line_description(item),
				"quote_qty": qty,
				"price": price,
				"line_total": line_total,
			})
		return rows, qty_total, amount_total

	def _quote_customer_choices(self, client, user):
		"""Rivhit customers that probably belong to this shop (phone match first)."""
		try:
			customers = cached_customers(client)
		except RivhitApiError as exc:
			return [], str(exc)
		matched = match_customers(customers, phone=user.contact_phone, name=user.company_name)
		if user.rivhit_customer_id and not any(int(c.get("customer_id") or 0) == user.rivhit_customer_id for c in matched):
			current = next((c for c in customers if int(c.get("customer_id") or 0) == user.rivhit_customer_id), None)
			if current:
				matched.insert(0, current)
		choices = [
			{"id": int(c["customer_id"]), "label": customer_display(c)}
			for c in matched if c.get("customer_id")
		]
		return choices, None

	def quote_order(self, request, object_id):
		order = get_object_or_404(
			WhiteOrder.objects.select_related("user").prefetch_related("items", "quotes"),
			pk=object_id,
		)
		user = order.user
		items = list(order.items.all())
		config_error = None if rivhit_token() else "לא הוגדר RIVHIT_API_TOKEN בהגדרות האתר (משתנה סביבה ב-Railway)."
		form_error = None
		qty_map = None
		customer_choices = []
		selected_customer = user.rivhit_customer_id or ""
		client = None

		if not config_error:
			client = get_rivhit_client()
			customer_choices, lookup_error = self._quote_customer_choices(client, user)
			if lookup_error:
				form_error = lookup_error

		if request.method == "POST" and not config_error:
			raw_customer = (request.POST.get("customer_id") or "").strip()
			selected_customer = raw_customer
			qty_map = {}
			try:
				for item in items:
					qty = int((request.POST.get(f"qty_{item.pk}") or "").strip())
					if qty < 0:
						raise ValueError
					qty_map[item.pk] = qty
			except (TypeError, ValueError):
				form_error = "כמות להצעה חייבת להיות מספר שלם (0 או יותר)."
			else:
				try:
					customer_id = int(raw_customer)
					if customer_id <= 0:
						raise ValueError
				except (TypeError, ValueError):
					customer_id = None
					form_error = "צריך לבחור לקוח בריווחית (או להקליד מזהה לקוח)."
			if not form_error:
				try:
					item_ids = cached_item_ids_by_barcode(client)
				except RivhitApiError:
					item_ids = {}
				rivhit_items, stored_lines = [], []
				for item in items:
					qty = qty_map[item.pk]
					if qty == 0:
						continue
					price = item.unit_price if item.unit_price is not None else Decimal("0")
					description = quote_line_description(item)
					rivhit_item_id = item_ids.get((item.barcode or "").strip(), 0)
					rivhit_items.append({
						"item_id": rivhit_item_id,
						"description": description,
						"quantity": qty,
						"price_nis": price,
					})
					stored_lines.append({
						"order_item_id": item.pk,
						"description": description,
						"barcode": item.barcode,
						"rivhit_item_id": rivhit_item_id,
						"order_quantity": item.quantity,
						"quote_quantity": qty,
						"pack_price": str(price),
					})
				if not rivhit_items:
					form_error = "צריך לפחות שורה אחת עם כמות גדולה מ־0."
				else:
					try:
						data = create_quote_document(customer_id, order.order_number, rivhit_items, client=client)
					except RivhitApiError as exc:
						form_error = str(exc)
					else:
						number = str(data.get("document_number") or "")
						link = data.get("document_link") or data.get("link_document") or ""
						WhiteQuote.objects.create(
							order=order,
							rivhit_customer_id=customer_id,
							rivhit_document_type=data.get("document_type") or None,
							rivhit_document_number=number,
							rivhit_document_identity=str(data.get("document_identity") or ""),
							rivhit_document_link=link,
							lines=stored_lines,
						)
						if user.rivhit_customer_id != customer_id:
							user.rivhit_customer_id = customer_id
							user.save(update_fields=["rivhit_customer_id"])
						if link:
							self.message_user(
								request,
								format_html(
									'הופקה הצעת מחיר {} בריווחית ללקוח {}. <a href="{}" target="_blank" rel="noopener">פתח PDF</a>',
									number or "—", customer_id, link,
								),
								messages.SUCCESS,
							)
						else:
							self.message_user(
								request,
								f"הופקה הצעת מחיר {number or '—'} בריווחית ללקוח {customer_id}.",
								messages.SUCCESS,
							)
						return HttpResponseRedirect(reverse("admin:white_catalog_whiteorder_change", args=[order.pk]))

		rows, quote_qty_total, quote_amount_total = self._quote_rows(items, qty_map)
		try:
			selected_customer_int = int(selected_customer)
		except (TypeError, ValueError):
			selected_customer_int = None
		context = {
			**self.admin_site.each_context(request),
			"title": f"הצעת מחיר בריווחית — {order.order_number}",
			"order": order,
			"rows": rows,
			"quote_qty_total": quote_qty_total,
			"quote_amount_total": quote_amount_total,
			"config_error": config_error,
			"form_error": form_error,
			"customer_choices": customer_choices,
			"selected_customer": selected_customer_int,
			"selected_in_choices": any(c["id"] == selected_customer_int for c in customer_choices),
			"quotes": order.quotes.all(),
			"opts": self.model._meta,
		}
		return render(request, "admin/white_catalog/order_quote.html", context)

	def print_order(self, request, object_id):
		order = get_object_or_404(
			WhiteOrder.objects.prefetch_related("items").select_related("user"),
			pk=object_id,
		)
		rows = []
		total_units = 0
		total_packs = 0
		for item in order.items.all():
			units = item.quantity * item.pack_quantity
			total_units += units
			total_packs += item.quantity
			rows.append({
				"item": item,
				"units": units,
				"line_total": item.get_line_total(),
			})
		return render(
			request,
			"admin/white_catalog/order_print.html",
			{
				"order": order,
				"rows": rows,
				"total_units": total_units,
				"total_packs": total_packs,
			},
		)

