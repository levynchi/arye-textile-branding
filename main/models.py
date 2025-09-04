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
	height_variant = models.CharField(
		"גובה",
		max_length=12,
		choices=(
			("auto", "אוטומטי"),
			("tall", "גבוה"),
			("short", "נמוך"),
		),
		default="auto",
		help_text="בחרו גובה הבאנר: אוטומטי לפי עמוד, או ציינו גבוה/נמוך ידנית",
	)
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
	link1 = models.CharField("קישור 1", max_length=200, blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא")
	image2 = models.ImageField("תמונה 2", upload_to="gallery/", blank=True, null=True)
	caption2 = models.CharField("שם קטגוריה 2", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	link2 = models.CharField("קישור 2", max_length=200, blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא")
	image3 = models.ImageField("תמונה 3", upload_to="gallery/", blank=True, null=True)
	caption3 = models.CharField("שם קטגוריה 3", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	link3 = models.CharField("קישור 3", max_length=200, blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא")
	image4 = models.ImageField("תמונה 4", upload_to="gallery/", blank=True, null=True)
	caption4 = models.CharField("שם קטגוריה 4", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	link4 = models.CharField("קישור 4", max_length=200, blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא")
	image5 = models.ImageField("תמונה 5", upload_to="gallery/", blank=True, null=True)
	caption5 = models.CharField("שם קטגוריה 5", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	link5 = models.CharField("קישור 5", max_length=200, blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא")
	image6 = models.ImageField("תמונה 6", upload_to="gallery/", blank=True, null=True)
	caption6 = models.CharField("שם קטגוריה 6", max_length=120, blank=True, help_text="הטקסט שמופיע על התמונה")
	link6 = models.CharField("קישור 6", max_length=200, blank=True, help_text="נתיב פנימי (למשל /branding/) או שם ניתוב (branding) או URL מלא")
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריית דף הבית"
		verbose_name_plural = "גלריית דף הבית"

	def __str__(self):  # pragma: no cover
		return self.title or f"Gallery #{self.pk}" 


class BrandingGallery(models.Model):
	"""Gallery of 9 images for the branding page only."""
	image1 = models.ImageField("תמונה 1", upload_to="branding_gallery/", blank=True, null=True)
	image2 = models.ImageField("תמונה 2", upload_to="branding_gallery/", blank=True, null=True)
	image3 = models.ImageField("תמונה 3", upload_to="branding_gallery/", blank=True, null=True)
	image4 = models.ImageField("תמונה 4", upload_to="branding_gallery/", blank=True, null=True)
	image5 = models.ImageField("תמונה 5", upload_to="branding_gallery/", blank=True, null=True)
	image6 = models.ImageField("תמונה 6", upload_to="branding_gallery/", blank=True, null=True)
	image7 = models.ImageField("תמונה 7", upload_to="branding_gallery/", blank=True, null=True)
	image8 = models.ImageField("תמונה 8", upload_to="branding_gallery/", blank=True, null=True)
	image9 = models.ImageField("תמונה 9", upload_to="branding_gallery/", blank=True, null=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריית מיתוג"
		verbose_name_plural = "גלריות מיתוג"

	def __str__(self):  # pragma: no cover
		return f"Branding Gallery #{self.pk}" if self.pk else "Branding Gallery"


class PrintingGallery(models.Model):
	"""Gallery of 12 images for the printing page only (3x4 grid)."""
	image1 = models.ImageField("תמונה 1", upload_to="printing_gallery/", blank=True, null=True)
	image2 = models.ImageField("תמונה 2", upload_to="printing_gallery/", blank=True, null=True)
	image3 = models.ImageField("תמונה 3", upload_to="printing_gallery/", blank=True, null=True)
	image4 = models.ImageField("תמונה 4", upload_to="printing_gallery/", blank=True, null=True)
	image5 = models.ImageField("תמונה 5", upload_to="printing_gallery/", blank=True, null=True)
	image6 = models.ImageField("תמונה 6", upload_to="printing_gallery/", blank=True, null=True)
	image7 = models.ImageField("תמונה 7", upload_to="printing_gallery/", blank=True, null=True)
	image8 = models.ImageField("תמונה 8", upload_to="printing_gallery/", blank=True, null=True)
	image9 = models.ImageField("תמונה 9", upload_to="printing_gallery/", blank=True, null=True)
	image10 = models.ImageField("תמונה 10", upload_to="printing_gallery/", blank=True, null=True)
	image11 = models.ImageField("תמונה 11", upload_to="printing_gallery/", blank=True, null=True)
	image12 = models.ImageField("תמונה 12", upload_to="printing_gallery/", blank=True, null=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריית הדפסות"
		verbose_name_plural = "גלריות הדפסות"

	def __str__(self):  # pragma: no cover
		return f"Printing Gallery #{self.pk}" if self.pk else "Printing Gallery"


class PatternmakingGallery(models.Model):
	"""Gallery of 9 images for the patternmaking (תדמיתנות וגזרנות) page."""
	image1 = models.ImageField("תמונה 1", upload_to="patternmaking_gallery/", blank=True, null=True)
	image2 = models.ImageField("תמונה 2", upload_to="patternmaking_gallery/", blank=True, null=True)
	image3 = models.ImageField("תמונה 3", upload_to="patternmaking_gallery/", blank=True, null=True)
	image4 = models.ImageField("תמונה 4", upload_to="patternmaking_gallery/", blank=True, null=True)
	image5 = models.ImageField("תמונה 5", upload_to="patternmaking_gallery/", blank=True, null=True)
	image6 = models.ImageField("תמונה 6", upload_to="patternmaking_gallery/", blank=True, null=True)
	image7 = models.ImageField("תמונה 7", upload_to="patternmaking_gallery/", blank=True, null=True)
	image8 = models.ImageField("תמונה 8", upload_to="patternmaking_gallery/", blank=True, null=True)
	image9 = models.ImageField("תמונה 9", upload_to="patternmaking_gallery/", blank=True, null=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריית תדמיתנות וגזרנות"
		verbose_name_plural = "גלריות תדמיתנות וגזרנות"

	def __str__(self):  # pragma: no cover
		return f"Patternmaking Gallery #{self.pk}" if self.pk else "Patternmaking Gallery"


class FabricsGallery(models.Model):
	"""Gallery of 9 images for the fabrics (בדים) page."""
	image1 = models.ImageField("תמונה 1", upload_to="fabrics_gallery/", blank=True, null=True)
	image2 = models.ImageField("תמונה 2", upload_to="fabrics_gallery/", blank=True, null=True)
	image3 = models.ImageField("תמונה 3", upload_to="fabrics_gallery/", blank=True, null=True)
	image4 = models.ImageField("תמונה 4", upload_to="fabrics_gallery/", blank=True, null=True)
	image5 = models.ImageField("תמונה 5", upload_to="fabrics_gallery/", blank=True, null=True)
	image6 = models.ImageField("תמונה 6", upload_to="fabrics_gallery/", blank=True, null=True)
	image7 = models.ImageField("תמונה 7", upload_to="fabrics_gallery/", blank=True, null=True)
	image8 = models.ImageField("תמונה 8", upload_to="fabrics_gallery/", blank=True, null=True)
	image9 = models.ImageField("תמונה 9", upload_to="fabrics_gallery/", blank=True, null=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריית בדים"
		verbose_name_plural = "גלריות בדים"

	def __str__(self):  # pragma: no cover
		return f"Fabrics Gallery #{self.pk}" if self.pk else "Fabrics Gallery"


class ManufacturingGallery(models.Model):
	"""Gallery of 9 images for the manufacturing (ייצור) page."""
	image1 = models.ImageField("תמונה 1", upload_to="manufacturing_gallery/", blank=True, null=True)
	image2 = models.ImageField("תמונה 2", upload_to="manufacturing_gallery/", blank=True, null=True)
	image3 = models.ImageField("תמונה 3", upload_to="manufacturing_gallery/", blank=True, null=True)
	image4 = models.ImageField("תמונה 4", upload_to="manufacturing_gallery/", blank=True, null=True)
	image5 = models.ImageField("תמונה 5", upload_to="manufacturing_gallery/", blank=True, null=True)
	image6 = models.ImageField("תמונה 6", upload_to="manufacturing_gallery/", blank=True, null=True)
	image7 = models.ImageField("תמונה 7", upload_to="manufacturing_gallery/", blank=True, null=True)
	image8 = models.ImageField("תמונה 8", upload_to="manufacturing_gallery/", blank=True, null=True)
	image9 = models.ImageField("תמונה 9", upload_to="manufacturing_gallery/", blank=True, null=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריית ייצור"
		verbose_name_plural = "גלריות ייצור"

	def __str__(self):  # pragma: no cover
		return f"Manufacturing Gallery #{self.pk}" if self.pk else "Manufacturing Gallery"


class PhotosGallery(models.Model):
	"""Standalone gallery page: up to 12 images."""
	image1 = models.ImageField("תמונה 1", upload_to="photos_gallery/", blank=True, null=True)
	image2 = models.ImageField("תמונה 2", upload_to="photos_gallery/", blank=True, null=True)
	image3 = models.ImageField("תמונה 3", upload_to="photos_gallery/", blank=True, null=True)
	image4 = models.ImageField("תמונה 4", upload_to="photos_gallery/", blank=True, null=True)
	image5 = models.ImageField("תמונה 5", upload_to="photos_gallery/", blank=True, null=True)
	image6 = models.ImageField("תמונה 6", upload_to="photos_gallery/", blank=True, null=True)
	image7 = models.ImageField("תמונה 7", upload_to="photos_gallery/", blank=True, null=True)
	image8 = models.ImageField("תמונה 8", upload_to="photos_gallery/", blank=True, null=True)
	image9 = models.ImageField("תמונה 9", upload_to="photos_gallery/", blank=True, null=True)
	image10 = models.ImageField("תמונה 10", upload_to="photos_gallery/", blank=True, null=True)
	image11 = models.ImageField("תמונה 11", upload_to="photos_gallery/", blank=True, null=True)
	image12 = models.ImageField("תמונה 12", upload_to="photos_gallery/", blank=True, null=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "גלריית תמונות"
		verbose_name_plural = "גלריות תמונות"

	def __str__(self):  # pragma: no cover
		return f"Photos Gallery #{self.pk}" if self.pk else "Photos Gallery"


class FooterSettings(models.Model):
	"""Site-wide footer contact and social links (singleton)."""
	phone_display = models.CharField("טלפון להצגה", max_length=40, blank=True, help_text="לדוגמה: 054-2367535")
	email = models.EmailField("אימייל", blank=True)
	whatsapp_link = models.URLField("קישור וואטסאפ", blank=True, help_text="לדוגמה: https://wa.me/9725...")
	instagram_url = models.URLField("קישור אינסטגרם", blank=True)
	facebook_url = models.URLField("קישור פייסבוק", blank=True)
	updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "הגדרות פוטר"
		verbose_name_plural = "הגדרות פוטר"

	def __str__(self):  # pragma: no cover
		return f"Footer Settings #{self.pk}" if self.pk else "Footer Settings"
