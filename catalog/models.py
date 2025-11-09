from django.db import models
from django.utils.text import slugify


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
	image = models.ImageField("תמונה", upload_to="catalog/subcategories/", blank=True, null=True)
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


class Product(models.Model):
	"""Product model - belongs to a Subcategory."""
	subcategory = models.ForeignKey(
		Subcategory,
		on_delete=models.CASCADE,
		related_name="products",
		verbose_name="תת-קטגוריה"
	)
	name = models.CharField("שם מוצר", max_length=200)
	description = models.TextField("תיאור", blank=True)
	image = models.ImageField("תמונה", upload_to="catalog/products/", blank=True, null=True)
	order = models.PositiveIntegerField("סדר תצוגה", default=0, help_text="מספר קטן = קודם")
	is_active = models.BooleanField("פעיל", default=True, help_text="האם להציג את המוצר בקטלוג")
	slug = models.SlugField("Slug", max_length=200, blank=True, help_text="יוצר אוטומטית מהשם")
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		app_label = "catalog"
		ordering = ("order", "name")
		verbose_name = "מוצר"
		verbose_name_plural = "מוצרים"
		unique_together = [["subcategory", "slug"]]

	def __str__(self):
		return self.name

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name, allow_unicode=True)
		super().save(*args, **kwargs)
