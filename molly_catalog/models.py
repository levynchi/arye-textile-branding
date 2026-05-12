"""Models for Molly Catalog – a private B2B order portal for the customer Molly.

Design notes
------------
- No prices anywhere. Molly only sees products and variants and places orders;
  pricing/fulfillment happens out of band.
- Variants are built from three orthogonal attributes: background color × print
  design × fabric type. The MollyVariant rows are the actual SKUs.
- A staff "admin action" can bulk-generate the cross-product of selected
  attribute values, so adding a new print or color does not require hand-creating
  every combination.
"""

from django.db import models
from django.utils.text import slugify
from django.contrib.auth.hashers import make_password, check_password


# ---------------------------------------------------------------------------
# Users & activity
# ---------------------------------------------------------------------------

class MollyCatalogUser(models.Model):
    """Login user for the Molly catalog.

    Kept separate from Django's auth.User so that Molly's access is fully
    isolated from staff/admin accounts.
    """

    display_name = models.CharField("שם להצגה", max_length=200, help_text="למשל: מולי")
    contact_phone = models.CharField("טלפון", max_length=20, blank=True)
    username = models.CharField("שם משתמש", max_length=150, unique=True)
    password_hash = models.CharField("סיסמא", max_length=128)
    is_active = models.BooleanField("פעיל", default=True)
    last_login = models.DateTimeField("כניסה אחרונה", null=True, blank=True)
    last_activity_at = models.DateTimeField("פעילות אחרונה", null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("display_name", "username")
        verbose_name = "משתמש קטלוג מולי"
        verbose_name_plural = "משתמשי קטלוג מולי"

    def __str__(self):
        return f"{self.display_name} ({self.username})"

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def update_activity(self):
        from django.utils import timezone
        self.last_activity_at = timezone.now()
        self.save(update_fields=["last_activity_at"])


class MollyCatalogUserActivity(models.Model):
    """One row per page visit by a Molly catalog user."""

    user = models.ForeignKey(
        MollyCatalogUser,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="משתמש",
    )
    timestamp = models.DateTimeField("זמן", auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField("כתובת IP", null=True, blank=True)
    user_agent = models.TextField("דפדפן", blank=True)
    page_url = models.CharField("דף", max_length=500)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("-timestamp",)
        verbose_name = "פעילות משתמש מולי"
        verbose_name_plural = "פעילויות משתמשי מולי"
        indexes = [models.Index(fields=["-timestamp", "user"])]

    def __str__(self):
        return f"{self.user.username} - {self.timestamp:%Y-%m-%d %H:%M:%S}"


# ---------------------------------------------------------------------------
# Variant attributes (the three axes that make up a SKU)
# ---------------------------------------------------------------------------

class MollyBackgroundColor(models.Model):
    """Background color value, e.g. "לבן", "ורוד", "שחור"."""

    name = models.CharField("שם צבע", max_length=80, unique=True)
    hex_color = models.CharField(
        "קוד HEX",
        max_length=9,
        blank=True,
        help_text='קוד צבע ל-CSS, למשל "#ffffff". משמש לתצוגת דוגמית.',
    )
    swatch_image = models.ImageField(
        "תמונת דוגמית",
        upload_to="molly_catalog/swatches/",
        blank=True,
        null=True,
        help_text="אופציונלי - תמונה קטנה שתוצג כדוגמית הצבע.",
    )
    order = models.PositiveIntegerField("סדר תצוגה", default=0)
    is_active = models.BooleanField("פעיל", default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("order", "name")
        verbose_name = "צבע רקע"
        verbose_name_plural = "צבעי רקע"

    def __str__(self):
        return self.name


class MollyPrintDesign(models.Model):
    """A printed design / pattern, e.g. "כוכבים קטנים שחורים"."""

    name = models.CharField("שם ההדפס", max_length=150, unique=True)
    description = models.TextField("תיאור", blank=True)
    preview_image = models.ImageField(
        "תצוגת הדפס",
        upload_to="molly_catalog/prints/",
        blank=True,
        null=True,
        help_text="תמונה של ההדפס שתוצג בבחירה.",
    )
    order = models.PositiveIntegerField("סדר תצוגה", default=0)
    is_active = models.BooleanField("פעיל", default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("order", "name")
        verbose_name = "הדפס"
        verbose_name_plural = "הדפסים"

    def __str__(self):
        return self.name


class MollyFabricType(models.Model):
    """A fabric type, e.g. "פליז", "כותנה", "טריקו"."""

    name = models.CharField("שם הבד", max_length=100, unique=True)
    description = models.TextField("תיאור", blank=True)
    order = models.PositiveIntegerField("סדר תצוגה", default=0)
    is_active = models.BooleanField("פעיל", default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("order", "name")
        verbose_name = "סוג בד"
        verbose_name_plural = "סוגי בדים"

    def __str__(self):
        return self.name


class MollyLabelColor(models.Model):
    """A label/tag color, e.g. "לבן", "שחור", "זהב".

    Unlike background color / print / fabric, the label color is a per-variant
    DEFAULT (set by Arye/Molly when seeding the catalog) – it is NOT something
    Molly chooses at order time, and it does NOT multiply the variant matrix.
    """

    name = models.CharField("שם צבע תווית", max_length=80, unique=True)
    hex_color = models.CharField(
        "קוד HEX",
        max_length=9,
        blank=True,
        help_text='קוד צבע ל-CSS, למשל "#000000". משמש לתצוגת דוגמית.',
    )
    swatch_image = models.ImageField(
        "תמונת דוגמית",
        upload_to="molly_catalog/label_swatches/",
        blank=True,
        null=True,
    )
    order = models.PositiveIntegerField("סדר תצוגה", default=0)
    is_active = models.BooleanField("פעיל", default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("order", "name")
        verbose_name = "צבע תווית"
        verbose_name_plural = "צבעי תוויות"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Catalog content
# ---------------------------------------------------------------------------

class MollyCategory(models.Model):
    """A grouping of products in Molly's catalog."""

    name = models.CharField("שם קטגוריה", max_length=200)
    description = models.TextField("תיאור", blank=True)
    image = models.ImageField(
        "תמונה",
        upload_to="molly_catalog/categories/",
        blank=True,
        null=True,
    )
    order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
    slug = models.SlugField("Slug", max_length=200, unique=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("order", "name")
        verbose_name = "קטגוריה"
        verbose_name_plural = "קטגוריות"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class MollyProduct(models.Model):
    """A product. Categories are optional – a standalone product appears on home."""

    category = models.ForeignKey(
        MollyCategory,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="קטגוריה",
        null=True,
        blank=True,
        help_text="השאר ריק כדי שהמוצר יופיע ישירות בעמוד הבית.",
    )
    name = models.CharField("שם מוצר", max_length=200)
    description = models.TextField("תיאור", blank=True)
    marketing_description = models.TextField(
        "תיאור שיווקי", blank=True, help_text="טקסט קצר שמופיע בכרטיס המוצר."
    )
    information = models.TextField(
        "מידע נוסף", blank=True, help_text="מפרט / חומרים / הנחיות שטיפה וכד'."
    )
    main_image = models.ImageField(
        "תמונה ראשית",
        upload_to="molly_catalog/products/",
        blank=True,
        null=True,
    )
    is_orderable = models.BooleanField(
        "זמין להזמנה", default=True, help_text="האם מולי יכולה להזמין את המוצר."
    )
    has_variants = models.BooleanField(
        "יש לו ואריאנטים",
        default=True,
        help_text="אם מסומן, מולי תבחר צבע/הדפס/בד. אחרת זה מוצר בודד.",
    )
    available_label_colors = models.ManyToManyField(
        MollyLabelColor,
        blank=True,
        related_name="products",
        verbose_name="צבעי תווית זמינים לבחירה",
        help_text=(
            "צבעי התווית שמולי תוכל לבחור מהם בעמוד המוצר. אם ריק - מולי "
            "תראה רק את צבע התווית של ברירת המחדל בלי אפשרות לשנות."
        ),
    )
    order = models.PositiveIntegerField("סדר תצוגה", default=0)
    slug = models.SlugField("Slug", max_length=200, unique=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("order", "name")
        verbose_name = "מוצר"
        verbose_name_plural = "מוצרים"

    def __str__(self):
        if self.category:
            return f"{self.category.name} - {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_main_image(self):
        if self.main_image:
            return self.main_image.url
        first = self.images.first()
        if first:
            return first.image.url
        return None

    def get_all_images(self):
        images = []
        if self.main_image:
            images.append({"url": self.main_image.url, "alt": self.name, "is_main": True})
        for img in self.images.all():
            images.append(
                {"url": img.image.url, "alt": img.alt_text or self.name, "is_main": False}
            )
        return images


class MollyProductImage(models.Model):
    """Extra gallery images for a product."""

    product = models.ForeignKey(
        MollyProduct,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="מוצר",
    )
    image = models.ImageField("תמונה", upload_to="molly_catalog/products/gallery/")
    alt_text = models.CharField("טקסט חלופי", max_length=200, blank=True)
    order = models.PositiveIntegerField("סדר תצוגה", default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("order", "created")
        verbose_name = "תמונת מוצר"
        verbose_name_plural = "תמונות מוצר"

    def __str__(self):
        return f"{self.product.name} - תמונה {self.order}"


class MollyVariant(models.Model):
    """One SKU = product + background color + print design + fabric type."""

    product = models.ForeignKey(
        MollyProduct,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="מוצר",
    )
    background_color = models.ForeignKey(
        MollyBackgroundColor,
        on_delete=models.PROTECT,
        related_name="variants",
        verbose_name="צבע רקע",
    )
    print_design = models.ForeignKey(
        MollyPrintDesign,
        on_delete=models.PROTECT,
        related_name="variants",
        verbose_name="הדפס",
    )
    fabric_type = models.ForeignKey(
        MollyFabricType,
        on_delete=models.PROTECT,
        related_name="variants",
        verbose_name="סוג בד",
    )
    default_label_color = models.ForeignKey(
        MollyLabelColor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="variants",
        verbose_name="צבע תווית ברירת מחדל",
        help_text="צבע התווית שיוצרק עם הוואריאנט הזה. לא חלק מקומבינציות הואריאנטים.",
    )
    image = models.ImageField(
        "תמונת ואריאנט",
        upload_to="molly_catalog/variants/",
        blank=True,
        null=True,
        help_text="אופציונלי - אם ריק נשתמש בתמונת המוצר.",
    )
    sku = models.CharField(
        "מק\"ט פנימי",
        max_length=80,
        blank=True,
        help_text="לשימוש פנימי של מולי / אריה.",
    )
    is_active = models.BooleanField("פעיל", default=True)
    order = models.PositiveIntegerField("סדר תצוגה", default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = (
            "order",
            "fabric_type__order",
            "background_color__order",
            "print_design__order",
        )
        verbose_name = "ואריאנט"
        verbose_name_plural = "ואריאנטים"
        unique_together = ("product", "background_color", "print_design", "fabric_type")

    def __str__(self):
        return (
            f"{self.product.name} | {self.fabric_type.name} | "
            f"{self.background_color.name} | {self.print_design.name}"
        )

    @property
    def display_name(self):
        return (
            f"{self.fabric_type.name} | {self.background_color.name} | "
            f"{self.print_design.name}"
        )

    def get_image_url(self):
        if self.image:
            return self.image.url
        return self.product.get_main_image()


# ---------------------------------------------------------------------------
# Cart & orders – no money fields anywhere
# ---------------------------------------------------------------------------

class MollyCart(models.Model):
    """Persistent server-side cart for the logged-in user."""

    STATUS_ACTIVE = "active"
    STATUS_SUBMITTED = "submitted"
    STATUS_ABANDONED = "abandoned"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "פעיל"),
        (STATUS_SUBMITTED, "הוגש"),
        (STATUS_ABANDONED, "נטוש"),
    ]

    user = models.ForeignKey(
        MollyCatalogUser,
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name="משתמש",
    )
    status = models.CharField(
        "סטטוס", max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("-created",)
        verbose_name = "עגלה"
        verbose_name_plural = "עגלות"

    def __str__(self):
        return f"עגלה #{self.pk} — {self.user.display_name} ({self.get_status_display()})"

    def get_item_count(self):
        return self.items.count()

    def get_total_quantity(self):
        return sum(item.quantity for item in self.items.all())


class MollyCartItem(models.Model):
    """One line in the cart. No price field – Molly never sees prices."""

    cart = models.ForeignKey(
        MollyCart, on_delete=models.CASCADE, related_name="items", verbose_name="עגלה"
    )
    product = models.ForeignKey(
        MollyProduct,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="מוצר",
    )
    variant = models.ForeignKey(
        MollyVariant,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="ואריאנט",
        null=True,
        blank=True,
    )
    selected_label_color = models.ForeignKey(
        MollyLabelColor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cart_items",
        verbose_name="צבע תווית שנבחר",
        help_text="הצבע שמולי בחרה. אם ריק, ייעשה fallback לברירת המחדל של הוואריאנט.",
    )
    quantity = models.PositiveIntegerField("כמות", default=1)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "molly_catalog"
        verbose_name = "פריט בעגלה"
        verbose_name_plural = "פריטים בעגלה"
        unique_together = ("cart", "variant", "selected_label_color")

    def __str__(self):
        if self.variant:
            return f"{self.product.name} | {self.variant.display_name} x{self.quantity}"
        return f"{self.product.name} | בלי ואריאנט x{self.quantity}"

    def display_variant_name(self):
        return self.variant.display_name if self.variant else "ללא ואריאנט"

    def get_image_url(self):
        if self.variant:
            return self.variant.get_image_url()
        return self.product.get_main_image()

    def effective_label_color(self):
        """The label color Molly will actually receive: her choice, or the variant default."""
        if self.selected_label_color_id:
            return self.selected_label_color
        if self.variant_id and self.variant.default_label_color_id:
            return self.variant.default_label_color
        return None


class MollyOrder(models.Model):
    """A submitted order. No total_amount – Arye computes pricing offline."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "ממתין"),
        (STATUS_PROCESSING, "בטיפול"),
        (STATUS_COMPLETED, "הושלם"),
        (STATUS_CANCELLED, "בוטל"),
    ]

    user = models.ForeignKey(
        MollyCatalogUser,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="לקוח",
    )
    cart = models.OneToOneField(
        MollyCart,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order",
        verbose_name="עגלה מקורית",
    )
    order_number = models.CharField(
        "מספר הזמנה", max_length=50, unique=True, blank=True
    )
    status = models.CharField(
        "סטטוס", max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    notes = models.TextField("הערות מולי", blank=True)
    admin_notes = models.TextField("הערות פנימיות", blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "molly_catalog"
        ordering = ("-created",)
        verbose_name = "הזמנה"
        verbose_name_plural = "הזמנות"

    def __str__(self):
        return f"הזמנה {self.order_number} — {self.user.display_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.order_number:
            from django.utils import timezone as tz
            self.order_number = f"MOL-{tz.now():%Y%m%d}-{self.pk:05d}"
            MollyOrder.objects.filter(pk=self.pk).update(order_number=self.order_number)

    def get_total_quantity(self):
        return sum(item.quantity for item in self.items.all())


class MollyOrderItem(models.Model):
    """Immutable line item snapshot from a submitted order."""

    order = models.ForeignKey(
        MollyOrder, on_delete=models.CASCADE, related_name="items", verbose_name="הזמנה"
    )
    product = models.ForeignKey(
        MollyProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="מוצר",
    )
    variant = models.ForeignKey(
        MollyVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="ואריאנט",
    )
    product_name = models.CharField("שם מוצר", max_length=200)
    background_color_name = models.CharField("צבע רקע", max_length=80, blank=True)
    print_design_name = models.CharField("הדפס", max_length=150, blank=True)
    fabric_type_name = models.CharField("סוג בד", max_length=100, blank=True)
    label_color_name = models.CharField("צבע תווית", max_length=80, blank=True)
    variant_sku = models.CharField("מק\"ט", max_length=80, blank=True)
    quantity = models.PositiveIntegerField("כמות")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "molly_catalog"
        verbose_name = "פריט הזמנה"
        verbose_name_plural = "פריטי הזמנה"

    def __str__(self):
        parts = [self.product_name]
        if self.fabric_type_name:
            parts.append(self.fabric_type_name)
        if self.background_color_name:
            parts.append(self.background_color_name)
        if self.print_design_name:
            parts.append(self.print_design_name)
        return " | ".join(parts) + f" x{self.quantity}"

    def display_variant_name(self):
        bits = [b for b in (
            self.fabric_type_name,
            self.background_color_name,
            self.print_design_name,
        ) if b]
        return " | ".join(bits) if bits else "ללא ואריאנט"
