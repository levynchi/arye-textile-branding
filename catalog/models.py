from django.db import models
from django.utils.text import slugify
from django.contrib.auth.hashers import make_password, check_password


class Category(models.Model):
	"""Category model for product catalog."""
	name = models.CharField("שם קטגוריה", max_length=200)
	description = models.TextField("תיאור", blank=True)
	image = models.ImageField("תמונה", upload_to="catalog/categories/", blank=True, null=True)
	order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
	slug = models.SlugField("Slug", max_length=200, unique=True, blank=True, help_text="יוצר אוטומטית מהשם")
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "catalog"
		ordering = ("order", "name")
		verbose_name = "קטגוריה"
		verbose_name_plural = "קטגוריות"

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name, allow_unicode=True)
		super().save(*args, **kwargs)


class Subcategory(models.Model):
	"""Subcategory model - belongs to a Category."""
	category = models.ForeignKey(
		Category,
		on_delete=models.CASCADE,
		related_name="subcategories",
		verbose_name="קטגוריה"
	)
	name = models.CharField("שם תת-קטגוריה", max_length=200)
	description = models.TextField("תיאור", blank=True)
	marketing_description = models.TextField("תיאור שיווקי", blank=True, help_text="תיאור שיווקי של המוצר - ניתן להזין HTML")
	information = models.TextField("מידע", blank=True, help_text="מידע כללי על המוצר - ניתן להזין HTML")
	pattern_and_branding = models.TextField("דפוס ומיתוג", blank=True, help_text="פרטים על דפוס ומיתוג - ניתן להזין HTML")
	fabric_production = models.TextField("אפשרות ייצור בדים", blank=True, help_text="אפשרויות ייצור בדים - ניתן להזין HTML")
	sizes = models.TextField("מידות", blank=True, help_text="מידות זמינות למוצר - ניתן להזין HTML")
	image = models.ImageField("תמונה ראשית", upload_to="catalog/subcategories/", blank=True, null=True, help_text="תמונה ראשית - מוצגת בכרטיס התת-קטגוריה")
	order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
	slug = models.SlugField("Slug", max_length=200, blank=True, help_text="יוצר אוטומטית מהשם")
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "catalog"
		ordering = ("order", "name")
		verbose_name = "תת-קטגוריה"
		verbose_name_plural = "תת-קטגוריות"
		unique_together = [["category", "slug"]]

	def __str__(self):
		return f"{self.category.name} - {self.name}"

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name, allow_unicode=True)
		super().save(*args, **kwargs)

	def get_main_image(self):
		"""Get the main image for the subcategory - either the primary image field or first SubcategoryImage."""
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


class SubcategoryImage(models.Model):
	"""Additional images for a subcategory."""
	subcategory = models.ForeignKey(
		Subcategory,
		on_delete=models.CASCADE,
		related_name="images",
		verbose_name="תת-קטגוריה"
	)
	image = models.ImageField("תמונה", upload_to="catalog/subcategories/gallery/")
	alt_text = models.CharField("טקסט חלופי", max_length=200, blank=True, help_text="תיאור התמונה - מומלץ למילוי")
	order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		app_label = "catalog"
		ordering = ("order", "created")
		verbose_name = "תמונת תת-קטגוריה"
		verbose_name_plural = "תמונות תת-קטגוריה"

	def __str__(self):
		return f"{self.subcategory.name} - תמונה {self.order}"


class CatalogUser(models.Model):
	"""Catalog user model for managing access to catalog pages."""
	company_name = models.CharField("שם העסק", max_length=200)
	contact_name = models.CharField("שם איש קשר", max_length=200)
	contact_phone = models.CharField("טלפון איש קשר", max_length=20)
	username = models.CharField("שם משתמש", max_length=150, unique=True)
	password_hash = models.CharField("סיסמא", max_length=128)
	is_active = models.BooleanField("פעיל", default=True, help_text="האם המשתמש יכול להתחבר")
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "catalog"
		ordering = ("company_name", "username")
		verbose_name = "משתמש קטלוג"
		verbose_name_plural = "משתמשי קטלוג"

	def __str__(self):
		return f"{self.company_name} ({self.username})"

	def set_password(self, raw_password):
		"""Hash and set the password."""
		self.password_hash = make_password(raw_password)

	def check_password(self, raw_password):
		"""Check if the provided password matches the stored hash."""
		return check_password(raw_password, self.password_hash)
