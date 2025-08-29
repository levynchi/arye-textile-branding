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


class Slide(models.Model):
	"""Single image for the horizontal scrolling slider."""
	image = models.ImageField(upload_to="slider/", blank=True, null=True, verbose_name="תמונה")
	alt = models.CharField("ALT", max_length=150, blank=True)
	order = models.PositiveIntegerField("סדר", default=0, help_text="מספר קטן = קודם")
	created = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ("order", "id")
		verbose_name = "תמונת סליידר"
		verbose_name_plural = "תמונות סליידר"

	def __str__(self):  # pragma: no cover
		return f"Slide #{self.pk} (order {self.order})"

class Banner(models.Model):
	"""Homepage hero banner image (single latest used)."""
	page = models.SlugField(
		"עמוד",
		max_length=50,
		blank=True,
		null=True,
		help_text="שם העמוד/slug (למשל: home, about, products). השאר ריק לבאנר כללי",
	)
	image = models.ImageField(upload_to="banner/", blank=True, null=True, help_text="תמונת באנר רקע (אופציונלי)")
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "באנר"
		verbose_name_plural = "באנרים"  # though usually only one

	def __str__(self):  # pragma: no cover
		label = self.page or "general"
		return f"Banner [{label}] #{self.pk}" if self.pk else f"Banner [{label}]"

	@classmethod
	def for_page(cls, page_slug: str | None):
		"""Get the most appropriate banner for a page.

		Priority: exact page match -> general (null/blank) -> any latest.
		"""
		qs = cls.objects
		if page_slug:
			obj = qs.filter(page__iexact=page_slug).order_by("-updated", "-id").first()
			if obj:
				return obj
		obj = qs.filter(models.Q(page__isnull=True) | models.Q(page__exact="")).order_by("-updated", "-id").first()
		return obj or qs.order_by("-updated", "-id").first()


class Gallery(models.Model):
	"""Simple gallery of up to six images for home page blocks."""
	title = models.CharField("כותרת (לא חובה)", max_length=120, blank=True, help_text="כותרת כללית לגלריה (אופציונלי)")
	image1 = models.ImageField("תמונה 1", upload_to="gallery/", blank=True, null=True)
	caption1 = models.CharField("שם קטגוריה 1", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	image2 = models.ImageField("תמונה 2", upload_to="gallery/", blank=True, null=True)
	caption2 = models.CharField("שם קטגוריה 2", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	image3 = models.ImageField("תמונה 3", upload_to="gallery/", blank=True, null=True)
	caption3 = models.CharField("שם קטגוריה 3", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	image4 = models.ImageField("תמונה 4", upload_to="gallery/", blank=True, null=True)
	caption4 = models.CharField("שם קטגוריה 4", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	image5 = models.ImageField("תמונה 5", upload_to="gallery/", blank=True, null=True)
	caption5 = models.CharField("שם קטגוריה 5", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	image6 = models.ImageField("תמונה 6", upload_to="gallery/", blank=True, null=True)
	caption6 = models.CharField("שם קטגוריה 6", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריה"
		verbose_name_plural = "גלריות"

	def __str__(self):  # pragma: no cover
		return self.title or f"Gallery #{self.pk}" 
