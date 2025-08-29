from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from .models import Gallery, Slide, BrandingGallery
from .forms import ContactRequestForm


def home(request):
	# Content blocks
	gallery = Gallery.objects.order_by("-updated", "-id").first()

	# Slides: all with images, ordered; duplicate list for seamless CSS loop
	slides_qs = Slide.objects.filter(image__isnull=False).order_by("order", "id")
	slides = list(slides_qs)
	slides_loop = slides + slides if slides else []

	# Contact form
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה, נחזור אליך בהקדם.")
			return redirect("home")
	else:
		form = ContactRequestForm()

	ctx = {
		"gallery": gallery,
		"slides": slides_loop,
		"contact_form": form,
	}
	return render(request, "home.html", ctx)


def branding(request):
	"""Branding page: header, hero, contact form, footer."""
	# Contact form (same handling as home)
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה, נחזור אליך בהקדם.")
			return redirect("branding")
	else:
		form = ContactRequestForm()

	# Branding gallery: take the latest configured one
	branding_gallery = BrandingGallery.objects.order_by("-updated", "-id").first()
	branding_images = []
	if branding_gallery:
		branding_images = [
			branding_gallery.image1,
			branding_gallery.image2,
			branding_gallery.image3,
			branding_gallery.image4,
			branding_gallery.image5,
			branding_gallery.image6,
			branding_gallery.image7,
			branding_gallery.image8,
			branding_gallery.image9,
		]

	ctx = {"contact_form": form, "branding_gallery": branding_gallery, "branding_images": branding_images}
	return render(request, "branding.html", ctx)


def printing(request):
	"""Printing page: header, hero, contact form, footer."""
	# Contact form handling
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה, נחזור אליך בהקדם.")
			return redirect("printing")
	else:
		form = ContactRequestForm()

	ctx = {"contact_form": form}
	return render(request, "printing.html", ctx)
