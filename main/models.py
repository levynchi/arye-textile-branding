from django.db import models


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
