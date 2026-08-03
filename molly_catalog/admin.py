"""Admin for the Molly catalog.

Key feature: the MollyProduct admin includes a custom action,
``generate_variant_matrix``, which presents an intermediate form letting the
operator pick which background colors, print designs and fabric types apply to
the selected products, then bulk-creates the full cross-product of variants in
one click (skipping combinations that already exist thanks to the
``unique_together`` constraint).
"""

from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, render
from django.urls import path
from django.utils.html import format_html, mark_safe

from .models import (
    MollyBackgroundColor,
    MollyCart,
    MollyCartItem,
    MollyCatalogUser,
    MollyCatalogUserActivity,
    MollyCategory,
    MollyFabricType,
    MollyLabelColor,
    MollyMockup,
    MollyMockupProduct,
    MollyOrder,
    MollyOrderItem,
    MollyPrintDesign,
    MollyProduct,
    MollyProductImage,
    MollyVariant,
)


# ---------------------------------------------------------------------------
# Attribute admins
# ---------------------------------------------------------------------------

@admin.register(MollyBackgroundColor)
class MollyBackgroundColorAdmin(admin.ModelAdmin):
    list_display = ("name", "hex_preview", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name",)

    def hex_preview(self, obj):
        if obj.hex_color:
            return format_html(
                '<span style="display:inline-block;width:24px;height:24px;'
                'border:1px solid #ccc;background:{};vertical-align:middle;"></span>'
                ' {}', obj.hex_color, obj.hex_color
            )
        return "-"
    hex_preview.short_description = "תצוגה"


@admin.register(MollyPrintDesign)
class MollyPrintDesignAdmin(admin.ModelAdmin):
    list_display = ("name", "preview_thumb", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name", "description")
    readonly_fields = ("preview_large",)

    def preview_thumb(self, obj):
        if obj.preview_image:
            return mark_safe(
                f'<img src="{obj.preview_image.url}" '
                'style="max-height:50px;max-width:80px;border-radius:4px;" />'
            )
        return "-"
    preview_thumb.short_description = "תצוגה"

    def preview_large(self, obj):
        if obj.preview_image:
            return mark_safe(
                f'<img src="{obj.preview_image.url}" '
                'style="max-height:300px;max-width:400px;border-radius:6px;" />'
            )
        return "אין תמונה"
    preview_large.short_description = "תצוגת ההדפס"


@admin.register(MollyFabricType)
class MollyFabricTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name", "description")


@admin.register(MollyLabelColor)
class MollyLabelColorAdmin(admin.ModelAdmin):
    list_display = ("name", "hex_preview", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name",)

    def hex_preview(self, obj):
        if obj.hex_color:
            return format_html(
                '<span style="display:inline-block;width:24px;height:24px;'
                'border:1px solid #ccc;background:{};vertical-align:middle;"></span>'
                ' {}', obj.hex_color, obj.hex_color
            )
        return "-"
    hex_preview.short_description = "תצוגה"


# ---------------------------------------------------------------------------
# Catalog content
# ---------------------------------------------------------------------------

class MollyProductImageInline(admin.TabularInline):
    model = MollyProductImage
    extra = 1
    fields = ("image_preview", "image", "alt_text", "order")
    readonly_fields = ("image_preview",)
    ordering = ("order",)

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="max-height:80px;max-width:120px;" />'
            )
        return "-"
    image_preview.short_description = "תצוגה"


class MollyVariantInline(admin.TabularInline):
    model = MollyVariant
    extra = 0
    fields = (
        "background_color",
        "print_design",
        "fabric_type",
        "default_label_color",
        "image",
        "sku",
        "is_active",
        "order",
    )
    show_change_link = True
    autocomplete_fields = ("background_color", "print_design", "fabric_type", "default_label_color")


class GenerateVariantMatrixForm(forms.Form):
    """Form used by the ``generate_variant_matrix`` admin action."""

    background_colors = forms.ModelMultipleChoiceField(
        queryset=MollyBackgroundColor.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="צבעי רקע",
    )
    print_designs = forms.ModelMultipleChoiceField(
        queryset=MollyPrintDesign.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="הדפסים",
    )
    fabric_types = forms.ModelMultipleChoiceField(
        queryset=MollyFabricType.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        label="סוגי בדים",
    )
    default_label_color = forms.ModelChoiceField(
        queryset=MollyLabelColor.objects.filter(is_active=True),
        required=False,
        label="צבע תווית ברירת מחדל (אופציונלי)",
        help_text="אם נבחר, ייקבע כברירת מחדל לכל הוואריאנטים החדשים שיווצרו.",
    )


@admin.register(MollyProduct)
class MollyProductAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category", "is_orderable", "has_variants", "variant_count", "order", "updated")
    list_editable = ("order",)
    list_filter = ("category", "is_orderable", "has_variants")
    search_fields = ("name", "slug", "description", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created", "updated")
    filter_horizontal = ("available_label_colors",)
    inlines = [MollyProductImageInline, MollyVariantInline]
    actions = ("generate_variant_matrix",)

    fieldsets = (
        (None, {
            "fields": ("category", "name", "slug", "main_image", "order", "is_orderable", "has_variants"),
        }),
        ("תיאורים", {
            "fields": ("description", "marketing_description", "information"),
        }),
        ("צבעי תוויות זמינים ללקוח לבחירה", {
            "fields": ("available_label_colors",),
            "description": (
                "אם משאירים ריק - מולי תראה רק את צבע התווית של ברירת המחדל לכל ואריאנט "
                "(שמוגדר על הוואריאנט עצמו). אם בוחרים כאן מספר צבעים, מולי תוכל לבחור "
                "בעמוד המוצר איזה צבע תווית היא רוצה מתוך הצבעים האלה."
            ),
        }),
        ("מידע נוסף", {
            "fields": ("created", "updated"),
            "classes": ("collapse",),
        }),
    )

    def variant_count(self, obj):
        return obj.variants.count()
    variant_count.short_description = "ואריאנטים"

    @admin.action(description="ייצר מטריצת ואריאנטים מצבע × הדפס × בד")
    def generate_variant_matrix(self, request, queryset):
        if "apply" in request.POST:
            form = GenerateVariantMatrixForm(request.POST)
            if form.is_valid():
                colors = list(form.cleaned_data["background_colors"])
                designs = list(form.cleaned_data["print_designs"])
                fabrics = list(form.cleaned_data["fabric_types"])
                default_label = form.cleaned_data.get("default_label_color")

                to_create = []
                for product in queryset:
                    for color in colors:
                        for design in designs:
                            for fabric in fabrics:
                                to_create.append(MollyVariant(
                                    product=product,
                                    background_color=color,
                                    print_design=design,
                                    fabric_type=fabric,
                                    default_label_color=default_label,
                                ))
                if to_create:
                    MollyVariant.objects.bulk_create(to_create, ignore_conflicts=True)

                self.message_user(
                    request,
                    f"נוצרו עד {len(to_create)} ואריאנטים פוטנציאליים עבור {queryset.count()} מוצרים "
                    "(קומבינציות שכבר היו קיימות דולגו).",
                    messages.SUCCESS,
                )
                return None
        else:
            form = GenerateVariantMatrixForm()

        context = {
            **self.admin_site.each_context(request),
            "title": "ייצור מטריצת ואריאנטים",
            "products": queryset,
            "form": form,
            "action": "generate_variant_matrix",
            "selected_action_pks": queryset.values_list("pk", flat=True),
            "opts": self.model._meta,
        }
        return render(request, "admin/molly_catalog/generate_variant_matrix.html", context)


@admin.register(MollyCategory)
class MollyCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "product_count", "created", "updated")
    list_editable = ("order",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created", "updated")

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "מוצרים"


@admin.register(MollyVariant)
class MollyVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "background_color",
        "print_design",
        "fabric_type",
        "default_label_color",
        "sku",
        "is_active",
        "order",
    )
    list_editable = ("default_label_color", "is_active", "order", "sku")
    list_filter = (
        "product",
        "background_color",
        "print_design",
        "fabric_type",
        "default_label_color",
        "is_active",
    )
    search_fields = ("product__name", "sku")
    autocomplete_fields = ("product", "background_color", "print_design", "fabric_type", "default_label_color")


# ---------------------------------------------------------------------------
# Mockups (הדמיות)
# ---------------------------------------------------------------------------

@admin.register(MollyMockupProduct)
class MollyMockupProductAdmin(admin.ModelAdmin):
    list_display = ("name", "image_thumb", "is_active", "order", "updated")
    list_editable = ("is_active", "order")
    search_fields = ("name",)
    readonly_fields = ("image_large", "created", "updated")

    fieldsets = (
        (None, {
            "fields": ("name", "image", "image_large", "order", "is_active"),
        }),
        ("מידע נוסף", {
            "fields": ("created", "updated"),
            "classes": ("collapse",),
        }),
    )

    def image_thumb(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" '
                'style="max-height:50px;max-width:80px;border-radius:4px;" />'
            )
        return "-"
    image_thumb.short_description = "תצוגה"

    def image_large(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" '
                'style="max-height:300px;max-width:400px;border-radius:6px;" />'
            )
        return "אין תמונה"
    image_large.short_description = "תצוגת המוצר"


@admin.register(MollyMockup)
class MollyMockupAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product_name", "result_thumb", "created")
    list_filter = ("user", "created")
    search_fields = ("product_name", "user__display_name", "user__username")
    readonly_fields = (
        "user", "mockup_product", "product_name", "print_image",
        "result_image", "result_large", "transform_data", "created",
    )
    date_hierarchy = "created"

    def has_add_permission(self, request):
        return False

    def result_thumb(self, obj):
        if obj.result_image:
            return mark_safe(
                f'<img src="{obj.result_image.url}" '
                'style="max-height:50px;max-width:80px;border-radius:4px;" />'
            )
        return "-"
    result_thumb.short_description = "הדמיה"

    def result_large(self, obj):
        if obj.result_image:
            return mark_safe(
                f'<img src="{obj.result_image.url}" '
                'style="max-height:400px;max-width:500px;border-radius:6px;" />'
            )
        return "אין תמונה"
    result_large.short_description = "תצוגת ההדמיה"


# ---------------------------------------------------------------------------
# Users & activity
# ---------------------------------------------------------------------------

class MollyCatalogUserActivityInline(admin.TabularInline):
    model = MollyCatalogUserActivity
    extra = 0
    max_num = 15
    can_delete = False
    fields = ("timestamp", "ip_address", "user_agent_short", "page_url")
    readonly_fields = ("timestamp", "ip_address", "user_agent_short", "page_url")
    ordering = ("-timestamp",)

    def user_agent_short(self, obj):
        if obj.user_agent and len(obj.user_agent) > 60:
            return obj.user_agent[:60] + "..."
        return obj.user_agent or "-"
    user_agent_short.short_description = "דפדפן"

    def has_add_permission(self, request, obj=None):
        return False


class MollyCatalogUserForm(forms.ModelForm):
    """Custom form for MollyCatalogUser with secure password handling."""

    password = forms.CharField(
        label="סיסמא",
        widget=forms.PasswordInput(attrs={"placeholder": "הכנסי סיסמא חדשה"}),
        required=False,
        help_text="השאר ריק כדי לשמור על הסיסמא הקיימת.",
    )

    class Meta:
        model = MollyCatalogUser
        fields = ("display_name", "contact_phone", "username", "is_active")

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        elif not user.pk:
            from django.utils.crypto import get_random_string
            user.set_password(get_random_string(16))
        if commit:
            user.save()
        return user


@admin.register(MollyCatalogUser)
class MollyCatalogUserAdmin(admin.ModelAdmin):
    form = MollyCatalogUserForm
    list_display = ("display_name", "username", "contact_phone", "is_active", "last_login", "created")
    list_editable = ("is_active",)
    list_filter = ("is_active", "created", "last_login")
    search_fields = ("display_name", "username", "contact_phone")
    readonly_fields = ("created", "updated", "last_login", "last_activity_at")
    inlines = [MollyCatalogUserActivityInline]

    fieldsets = (
        ("פרטי משתמש", {
            "fields": ("display_name", "contact_phone")
        }),
        ("התחברות", {
            "fields": ("username", "password", "is_active"),
        }),
        ("פעילות", {
            "fields": ("last_login", "last_activity_at"),
            "classes": ("wide",),
        }),
        ("מידע נוסף", {
            "fields": ("created", "updated"),
            "classes": ("collapse",),
        }),
    )


@admin.register(MollyCatalogUserActivity)
class MollyCatalogUserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "timestamp", "ip_address", "page_url")
    list_filter = ("user", "timestamp")
    search_fields = ("user__username", "user__display_name", "ip_address", "page_url")
    readonly_fields = ("user", "timestamp", "ip_address", "user_agent", "page_url")
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Cart & orders
# ---------------------------------------------------------------------------

class MollyCartItemInline(admin.TabularInline):
    model = MollyCartItem
    extra = 0
    readonly_fields = ("product", "variant", "selected_label_color", "quantity", "created")
    fields = ("product", "variant", "selected_label_color", "quantity", "created")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MollyCart)
class MollyCartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "get_item_count", "created", "updated")
    list_filter = ("status", "created")
    search_fields = ("user__display_name", "user__username")
    readonly_fields = ("user", "status", "created", "updated")
    inlines = [MollyCartItemInline]

    def has_add_permission(self, request):
        return False


class MollyOrderItemInline(admin.TabularInline):
    model = MollyOrderItem
    extra = 0
    readonly_fields = (
        "product_name",
        "fabric_type_name",
        "background_color_name",
        "print_design_name",
        "label_color_name",
        "variant_sku",
        "quantity",
    )
    fields = (
        "product_name",
        "fabric_type_name",
        "background_color_name",
        "print_design_name",
        "label_color_name",
        "variant_sku",
        "quantity",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(MollyOrder)
class MollyOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "item_count", "created", "updated")
    list_editable = ("status",)
    list_filter = ("status", "created")
    search_fields = ("order_number", "user__display_name", "user__username")
    readonly_fields = ("order_number", "user", "cart", "created", "updated")
    inlines = [MollyOrderItemInline]
    change_form_template = "admin/molly_catalog/mollyorder_change_form.html"

    fieldsets = (
        ("פרטי הזמנה", {
            "fields": ("order_number", "user", "status", "created", "updated"),
        }),
        ("הערות", {
            "fields": ("notes", "admin_notes"),
        }),
    )

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = "פריטים"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:object_id>/print/",
                self.admin_site.admin_view(self.print_order),
                name="molly_catalog_mollyorder_print",
            ),
        ]
        return custom + urls

    def print_order(self, request, object_id):
        order = get_object_or_404(
            MollyOrder.objects.prefetch_related("items").select_related("user"),
            pk=object_id,
        )
        return render(request, "admin/molly_catalog/order_print.html", {"order": order})
