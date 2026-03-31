from django.db import models
from django.utils.text import slugify
from django.contrib.auth.hashers import make_password, check_password
from tinymce.models import HTMLField


class WhiteCategory(models.Model):
	"""Category model for white catalog."""
	name = models.CharField("שם קטגוריה", max_length=200)
	description = models.TextField("תיאור", blank=True)
	image = models.ImageField("תמונה", upload_to="white_catalog/categories/", blank=True, null=True)
	order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
	slug = models.SlugField("Slug", max_length=200, unique=True, blank=True, help_text="יוצר אוטומטית מהשם")
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("order", "name")
		verbose_name = "קטגוריה לבנה"
		verbose_name_plural = "קטגוריות לבנות"

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name, allow_unicode=True)
		super().save(*args, **kwargs)


class WhiteSubcategory(models.Model):
	"""Subcategory model - belongs to a WhiteCategory."""
	is_orderable = models.BooleanField(
		"זמין להזמנה",
		default=False,
		help_text="האם מוצר זה נכלל במערכת ההזמנות (גרסאות + מארזים)"
	)
	category = models.ForeignKey(
		WhiteCategory,
		on_delete=models.CASCADE,
		related_name="subcategories",
		verbose_name="קטגוריה",
		null=True,
		blank=True,
		help_text="השאר ריק אם תרצה שהתת-קטגוריה תופיע כקטגוריה בעמוד הראשי"
	)
	name = models.CharField("שם תת-קטגוריה", max_length=200)
	description = models.TextField("תיאור", blank=True)
	marketing_description = HTMLField("תיאור שיווקי", blank=True, help_text="תיאור שיווקי של המוצר")
	information = HTMLField("מידע", blank=True, help_text="מידע כללי על המוצר")
	pattern_and_branding = HTMLField("דפוס ומיתוג", blank=True, help_text="פרטים על דפוס ומיתוג")
	fabric_production = HTMLField("אפשרות ייצור בדים", blank=True, help_text="אפשרויות ייצור בדים")
	sizes = HTMLField("מידות", blank=True, help_text="מידות זמינות למוצר")
	unit_price = models.DecimalField("מחיר סיטונאי (לא כולל מע\"מ)", max_digits=10, decimal_places=2, blank=True, null=True, help_text="מחיר סיטונאי בשקלים - לא כולל מע\"מ")
	online_price = models.DecimalField("מחיר קמעונאי מומלץ (לא כולל מע\"מ)", max_digits=10, decimal_places=2, blank=True, null=True, help_text="מחיר מומלץ למכירה באתר החנות ללקוח הסופי - לא כולל מע\"מ")
	image = models.ImageField("תמונה ראשית", upload_to="white_catalog/subcategories/", blank=True, null=True, help_text="תמונה ראשית - מוצגת בכרטיס התת-קטגוריה")
	order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
	slug = models.SlugField("Slug", max_length=200, unique=True, blank=True, help_text="יוצר אוטומטית מהשם")
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("order", "name")
		verbose_name = "תת-קטגוריה לבנה"
		verbose_name_plural = "תת-קטגוריות לבנות"

	def __str__(self):
		if self.category:
			return f"{self.category.name} - {self.name}"
		return self.name

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name, allow_unicode=True)
		super().save(*args, **kwargs)

	def get_main_image(self):
		"""Get the main image for the subcategory - either the primary image field or first WhiteSubcategoryImage."""
		if self.image:
			return self.image.url
		# Try to get first subcategory image
		first_image = self.images.first()
		if first_image:
			return first_image.image.url
		return None

	def get_all_images(self):
		"""Get all images for the subcategory including the main image."""
		images = []
		if self.image:
			images.append({'url': self.image.url, 'alt': self.name, 'is_main': True})
		for img in self.images.all():
			images.append({'url': img.image.url, 'alt': img.alt_text or self.name, 'is_main': False})
		return images

	def has_size_prices(self):
		"""Check if this subcategory has size-based pricing."""
		return self.size_prices.exists()

	def get_price_range(self):
		"""Get the min and max price range for size-based pricing.
		
		Returns:
			tuple: (min_price, max_price) or None if no size prices exist
		"""
		prices = self.size_prices.all()
		if not prices:
			return None
		
		price_values = [p.price for p in prices]
		return (min(price_values), max(price_values))


class WhiteSubcategoryImage(models.Model):
	"""Additional images for a white subcategory."""
	subcategory = models.ForeignKey(
		WhiteSubcategory,
		on_delete=models.CASCADE,
		related_name="images",
		verbose_name="תת-קטגוריה"
	)
	image = models.ImageField("תמונה", upload_to="white_catalog/subcategories/gallery/")
	alt_text = models.CharField("טקסט חלופי", max_length=200, blank=True, help_text="תיאור התמונה - מומלץ למילוי")
	order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("order", "created")
		verbose_name = "תמונת תת-קטגוריה לבנה"
		verbose_name_plural = "תמונות תת-קטגוריה לבנה"

	def __str__(self):
		return f"{self.subcategory.name} - תמונה {self.order}"


class WhiteSubcategoryPrice(models.Model):
	"""Price per size for a white subcategory."""
	subcategory = models.ForeignKey(
		WhiteSubcategory,
		on_delete=models.CASCADE,
		related_name="size_prices",
		verbose_name="תת-קטגוריה"
	)
	size_name = models.CharField("שם המידה", max_length=50, help_text="למשל: S, M, L, XL, 2-4, 6-8")
	price = models.DecimalField("מחיר (לא כולל מע\"מ)", max_digits=10, decimal_places=2, help_text="מחיר למידה זו בשקלים - לא כולל מע\"מ")
	order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("order", "id")
		verbose_name = "מחיר למידה"
		verbose_name_plural = "מחירים למידות"

	def __str__(self):
		return f"{self.subcategory.name} - {self.size_name}: ₪{self.price}"


class WhiteCatalogUser(models.Model):
	"""White catalog user model for managing access to white catalog pages."""
	company_name = models.CharField("שם העסק", max_length=200)
	contact_name = models.CharField("שם איש קשר", max_length=200)
	contact_phone = models.CharField("טלפון איש קשר", max_length=20)
	username = models.CharField("שם משתמש", max_length=150, unique=True)
	password_hash = models.CharField("סיסמא", max_length=128)
	is_active = models.BooleanField("פעיל", default=True, help_text="האם המשתמש יכול להתחבר")
	last_login = models.DateTimeField("כניסה אחרונה", null=True, blank=True)
	last_activity_at = models.DateTimeField("פעילות אחרונה", null=True, blank=True)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("company_name", "username")
		verbose_name = "משתמש קטלוג לבן"
		verbose_name_plural = "משתמשי קטלוג לבן"

	def __str__(self):
		return f"{self.company_name} ({self.username})"

	def set_password(self, raw_password):
		"""Hash and set the password."""
		self.password_hash = make_password(raw_password)

	def check_password(self, raw_password):
		"""Check if the provided password matches the stored hash."""
		return check_password(raw_password, self.password_hash)
	
	def update_activity(self):
		"""Update the last activity timestamp."""
		from django.utils import timezone
		self.last_activity_at = timezone.now()
		self.save(update_fields=['last_activity_at'])


class WhiteCatalogUserActivity(models.Model):
	"""Activity log for white catalog users - tracks every page visit."""
	user = models.ForeignKey(
		WhiteCatalogUser,
		on_delete=models.CASCADE,
		related_name="activities",
		verbose_name="משתמש"
	)
	timestamp = models.DateTimeField("זמן", auto_now_add=True, db_index=True)
	ip_address = models.GenericIPAddressField("כתובת IP", null=True, blank=True)
	user_agent = models.TextField("דפדפן", blank=True)
	page_url = models.CharField("דף", max_length=500)
	
	class Meta:
		app_label = "white_catalog"
		ordering = ("-timestamp",)
		verbose_name = "פעילות משתמש"
		verbose_name_plural = "פעילויות משתמשים"
		indexes = [
			models.Index(fields=['-timestamp', 'user']),
		]
	
	def __str__(self):
		return f"{self.user.username} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


# ---------------------------------------------------------------------------
# Ordering system models
# ---------------------------------------------------------------------------

class WhitePackType(models.Model):
	"""Global pack type definition — e.g. מארז שלישיות (x3), מארז חמישיות (x5)."""
	name = models.CharField("שם מארז", max_length=100, help_text="למשל: מארז שלישיות, מארז חמישיות")
	quantity = models.PositiveIntegerField("כמות יחידות במארז", help_text="למשל: 3 או 5")
	order = models.PositiveIntegerField("סדר תצוגה", default=0)
	is_active = models.BooleanField("פעיל", default=True)
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("order", "quantity")
		verbose_name = "סוג מארז"
		verbose_name_plural = "סוגי מארזים"

	def __str__(self):
		return f"{self.name} (x{self.quantity})"


class WhiteProductVariant(models.Model):
	"""A fabric/material variant of a product — e.g. טריקו, פלנל."""
	product = models.ForeignKey(
		WhiteSubcategory,
		on_delete=models.CASCADE,
		related_name="variants",
		verbose_name="מוצר"
	)
	name = models.CharField("שם חומר/גרסה", max_length=100, help_text="למשל: טריקו, פלנל, כותנה")
	description = models.TextField("תיאור", blank=True)
	is_active = models.BooleanField("פעיל", default=True)
	order = models.PositiveIntegerField("סדר תצוגה", default=0)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("order", "name")
		verbose_name = "גרסת מוצר"
		verbose_name_plural = "גרסאות מוצר"
		unique_together = ("product", "name")

	def __str__(self):
		return f"{self.product.name} — {self.name}"


class WhiteVariantSize(models.Model):
	"""A size available for a specific variant — each variant has its own size list."""
	variant = models.ForeignKey(
		WhiteProductVariant,
		on_delete=models.CASCADE,
		related_name="sizes",
		verbose_name="גרסה"
	)
	size_name = models.CharField("מידה", max_length=50, help_text="למשל: 0-3, 3-6, 6-12, 12-18, 18-24")
	order = models.PositiveIntegerField("סדר תצוגה", default=0)
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("order", "id")
		verbose_name = "מידה לגרסה"
		verbose_name_plural = "מידות לגרסה"
		unique_together = ("variant", "size_name")

	def __str__(self):
		return f"{self.variant} — {self.size_name}"


class WhiteVariantPackPrice(models.Model):
	"""Price for a specific size + pack-type combination on a variant."""
	variant_size = models.ForeignKey(
		WhiteVariantSize,
		on_delete=models.CASCADE,
		related_name="pack_prices",
		verbose_name="מידה"
	)
	pack_type = models.ForeignKey(
		WhitePackType,
		on_delete=models.CASCADE,
		related_name="variant_prices",
		verbose_name="סוג מארז"
	)
	price = models.DecimalField(
		"מחיר (לא כולל מע\"מ)",
		max_digits=10,
		decimal_places=2,
		help_text="מחיר למארז בשקלים — לא כולל מע\"מ"
	)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "white_catalog"
		verbose_name = "מחיר מארז לפי מידה"
		verbose_name_plural = "מחירי מארזים לפי מידה"
		unique_together = ("variant_size", "pack_type")

	def __str__(self):
		return f"{self.variant_size} | {self.pack_type} = ₪{self.price}"


class WhiteCart(models.Model):
	"""Server-side shopping cart for a logged-in B2B user."""
	STATUS_ACTIVE = "active"
	STATUS_SUBMITTED = "submitted"
	STATUS_ABANDONED = "abandoned"
	STATUS_CHOICES = [
		(STATUS_ACTIVE, "פעיל"),
		(STATUS_SUBMITTED, "הוגש"),
		(STATUS_ABANDONED, "נטוש"),
	]

	user = models.ForeignKey(
		WhiteCatalogUser,
		on_delete=models.CASCADE,
		related_name="carts",
		verbose_name="משתמש"
	)
	status = models.CharField("סטטוס", max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("-created",)
		verbose_name = "עגלת קניות"
		verbose_name_plural = "עגלות קניות"

	def __str__(self):
		return f"עגלה #{self.pk} — {self.user.company_name} ({self.get_status_display()})"

	def get_total(self):
		return sum(item.get_line_total() for item in self.items.select_related("pack_type"))

	def get_item_count(self):
		return self.items.count()


class WhiteCartItem(models.Model):
	"""One line in the cart: variant + size + pack-type + quantity."""
	cart = models.ForeignKey(WhiteCart, on_delete=models.CASCADE, related_name="items", verbose_name="עגלה")
	product = models.ForeignKey(WhiteSubcategory, on_delete=models.CASCADE, related_name="cart_items", verbose_name="מוצר")
	variant = models.ForeignKey(WhiteProductVariant, on_delete=models.CASCADE, related_name="cart_items", verbose_name="גרסה")
	variant_size = models.ForeignKey(WhiteVariantSize, on_delete=models.CASCADE, related_name="cart_items", verbose_name="מידה")
	pack_type = models.ForeignKey(WhitePackType, on_delete=models.CASCADE, related_name="cart_items", verbose_name="סוג מארז")
	quantity = models.PositiveIntegerField("כמות מארזים", default=1)
	price_at_add = models.DecimalField("מחיר בעת הוספה", max_digits=10, decimal_places=2)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "white_catalog"
		verbose_name = "פריט בעגלה"
		verbose_name_plural = "פריטים בעגלה"
		unique_together = ("cart", "variant_size", "pack_type")

	def __str__(self):
		return (
			f"{self.product.name} | {self.variant.name} | "
			f"{self.variant_size.size_name} | {self.pack_type.name} x{self.quantity}"
		)

	def get_line_total(self):
		return self.price_at_add * self.quantity


class WhiteOrder(models.Model):
	"""A submitted order created when the user checks out."""
	STATUS_PENDING = "pending"
	STATUS_CONFIRMED = "confirmed"
	STATUS_PROCESSING = "processing"
	STATUS_SHIPPED = "shipped"
	STATUS_DELIVERED = "delivered"
	STATUS_CANCELLED = "cancelled"
	STATUS_CHOICES = [
		(STATUS_PENDING, "ממתין לאישור"),
		(STATUS_CONFIRMED, "אושר"),
		(STATUS_PROCESSING, "בטיפול"),
		(STATUS_SHIPPED, "נשלח"),
		(STATUS_DELIVERED, "נמסר"),
		(STATUS_CANCELLED, "בוטל"),
	]

	user = models.ForeignKey(
		WhiteCatalogUser,
		on_delete=models.PROTECT,
		related_name="orders",
		verbose_name="לקוח"
	)
	cart = models.OneToOneField(
		WhiteCart,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="order",
		verbose_name="עגלה מקורית"
	)
	order_number = models.CharField("מספר הזמנה", max_length=50, unique=True, blank=True)
	status = models.CharField("סטטוס", max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	notes = models.TextField("הערות לקוח", blank=True)
	admin_notes = models.TextField("הערות פנימיות", blank=True)
	total_amount = models.DecimalField("סה\"כ (לא כולל מע\"מ)", max_digits=12, decimal_places=2)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "white_catalog"
		ordering = ("-created",)
		verbose_name = "הזמנה"
		verbose_name_plural = "הזמנות"

	def __str__(self):
		return f"הזמנה {self.order_number} — {self.user.company_name}"

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		if not self.order_number:
			from django.utils import timezone as tz
			self.order_number = f"ORD-{tz.now().strftime('%Y%m%d')}-{self.pk:05d}"
			WhiteOrder.objects.filter(pk=self.pk).update(order_number=self.order_number)


class WhiteOrderItem(models.Model):
	"""Immutable line item on a submitted order — all values snapshotted."""
	order = models.ForeignKey(WhiteOrder, on_delete=models.CASCADE, related_name="items", verbose_name="הזמנה")
	# Live FK references (nullable — for admin drill-through only)
	product = models.ForeignKey(WhiteSubcategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items", verbose_name="מוצר")
	variant = models.ForeignKey(WhiteProductVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items", verbose_name="גרסה")
	# Snapshot fields — never change after creation
	product_name = models.CharField("שם מוצר", max_length=200)
	variant_name = models.CharField("גרסה", max_length=100)
	size_name = models.CharField("מידה", max_length=50)
	pack_type_name = models.CharField("סוג מארז", max_length=100)
	pack_quantity = models.PositiveIntegerField("יחידות במארז")
	quantity = models.PositiveIntegerField("כמות מארזים")
	unit_price = models.DecimalField("מחיר למארז (לא כולל מע\"מ)", max_digits=10, decimal_places=2)

	class Meta:
		app_label = "white_catalog"
		verbose_name = "פריט הזמנה"
		verbose_name_plural = "פריטי הזמנה"

	def __str__(self):
		return (
			f"{self.product_name} | {self.variant_name} | "
			f"{self.size_name} | {self.pack_type_name} x{self.quantity}"
		)

	def get_line_total(self):
		return self.unit_price * self.quantity

