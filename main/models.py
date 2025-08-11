from django.db import models


class ContactRequest(models.Model):
	"""Contact form submissions stored in DB."""
	full_name = models.CharField("שם מלא", max_length=120)
	company = models.CharField("חברה", max_length=120, blank=True)
	email = models.EmailField("אימייל")
	phone = models.CharField("טלפון", max_length=40, blank=True)
	message = models.TextField("תיאור הבקשה", blank=True)
	created = models.DateTimeField(auto_now_add=True)
	answered = models.BooleanField("טופל", default=False)

	class Meta:
		ordering = ("-created",)
		verbose_name = "פניית יצירת קשר"
		verbose_name_plural = "פניות יצירת קשר"

	def __str__(self):  # pragma: no cover
		return f"{self.full_name} - {self.created:%Y-%m-%d}" 

class Banner(models.Model):
	"""Homepage hero banner image (single latest used)."""
	image = models.ImageField(upload_to="banner/", blank=True, null=True, help_text="תמונת באנר רקע (אופציונלי)")
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "באנר"
		verbose_name_plural = "באנרים"  # though usually only one

	def __str__(self):  # pragma: no cover
		return f"Banner #{self.pk}" if self.pk else "Banner"


class Gallery(models.Model):
	"""Simple gallery of up to six images for home page blocks."""
	title = models.CharField(max_length=120, blank=True, help_text="Optional overall gallery title")
	image1 = models.ImageField(upload_to="gallery/", blank=True, null=True)
	caption1 = models.CharField(max_length=120, blank=True)
	image2 = models.ImageField(upload_to="gallery/", blank=True, null=True)
	caption2 = models.CharField(max_length=120, blank=True)
	image3 = models.ImageField(upload_to="gallery/", blank=True, null=True)
	caption3 = models.CharField(max_length=120, blank=True)
	image4 = models.ImageField(upload_to="gallery/", blank=True, null=True)
	caption4 = models.CharField(max_length=120, blank=True)
	image5 = models.ImageField(upload_to="gallery/", blank=True, null=True)
	caption5 = models.CharField(max_length=120, blank=True)
	image6 = models.ImageField(upload_to="gallery/", blank=True, null=True)
	caption6 = models.CharField(max_length=120, blank=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריה"
		verbose_name_plural = "גלריות"

	def __str__(self):  # pragma: no cover
		return self.title or f"Gallery #{self.pk}" 
