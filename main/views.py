from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from .models import Gallery, Slide, BrandingGallery, PrintingGallery, PatternmakingGallery, FabricsGallery, ManufacturingGallery, CuttingGallery, PhotosGallery
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

	# Printing gallery: latest configured
	printing_gallery = PrintingGallery.objects.order_by("-updated", "-id").first()
	printing_images = []
	if printing_gallery:
		printing_images = [
			printing_gallery.image1,
			printing_gallery.image2,
			printing_gallery.image3,
			printing_gallery.image4,
			printing_gallery.image5,
			printing_gallery.image6,
			printing_gallery.image7,
			printing_gallery.image8,
			printing_gallery.image9,
			printing_gallery.image10,
			printing_gallery.image11,
			printing_gallery.image12,
		]

	ctx = {"contact_form": form, "printing_gallery": printing_gallery, "printing_images": printing_images}
	return render(request, "printing.html", ctx)


def patternmaking(request):
	"""Patternmaking page: header, hero, contact form, footer."""
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה, נחזור אליך בהקדם.")
			return redirect("patternmaking")
	else:
		form = ContactRequestForm()

	pattern_gallery = PatternmakingGallery.objects.order_by("-updated", "-id").first()
	pattern_images = []
	if pattern_gallery:
		pattern_images = [
			pattern_gallery.image1,
			pattern_gallery.image2,
			pattern_gallery.image3,
			pattern_gallery.image4,
			pattern_gallery.image5,
			pattern_gallery.image6,
			pattern_gallery.image7,
			pattern_gallery.image8,
			pattern_gallery.image9,
		]

	ctx = {"contact_form": form, "pattern_gallery": pattern_gallery, "pattern_images": pattern_images}
	return render(request, "patternmaking.html", ctx)


def fabrics(request):
	"""Fabrics page: header, hero, contact form, footer."""
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה, נחזור אליך בהקדם.")
			return redirect("fabrics")
	else:
		form = ContactRequestForm()

	fabrics_gallery = FabricsGallery.objects.order_by("-updated", "-id").first()
	fabrics_images = []
	if fabrics_gallery:
		fabrics_images = [
			fabrics_gallery.image1,
			fabrics_gallery.image2,
			fabrics_gallery.image3,
			fabrics_gallery.image4,
			fabrics_gallery.image5,
			fabrics_gallery.image6,
			fabrics_gallery.image7,
			fabrics_gallery.image8,
			fabrics_gallery.image9,
		]

	ctx = {"contact_form": form, "fabrics_gallery": fabrics_gallery, "fabrics_images": fabrics_images}
	return render(request, "fabrics.html", ctx)


def manufacturing(request):
	"""Manufacturing page: header, hero, contact form, footer."""
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה, נחזור אליך בהקדם.")
			return redirect("manufacturing")
	else:
		form = ContactRequestForm()

	manuf_gallery = ManufacturingGallery.objects.order_by("-updated", "-id").first()
	manuf_images = []
	if manuf_gallery:
		manuf_images = [
			manuf_gallery.image1,
			manuf_gallery.image2,
			manuf_gallery.image3,
			manuf_gallery.image4,
			manuf_gallery.image5,
			manuf_gallery.image6,
			manuf_gallery.image7,
			manuf_gallery.image8,
			manuf_gallery.image9,
		]

	ctx = {"contact_form": form, "manuf_gallery": manuf_gallery, "manuf_images": manuf_images}
	return render(request, "manufacturing.html", ctx)


def about(request):
	"""About page with company intro and why-us section."""
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה, נחזור אליך בהקדם.")
			return redirect("about")
	else:
		form = ContactRequestForm()

	ctx = {"contact_form": form}
	return render(request, "about.html", ctx)


def dev_debug(request):
	"""Return basic request/env info to help debug local HTTP/HTTPS issues (DEBUG only)."""
	meta = request.META
	info = {
		"path": request.path,
		"method": request.method,
		"is_secure": request.is_secure(),
		"scheme": request.scheme,
		"server_protocol": meta.get("SERVER_PROTOCOL"),
		"http_host": meta.get("HTTP_HOST"),
		"host": request.get_host(),
		"remote_addr": meta.get("REMOTE_ADDR"),
		"x_forwarded_proto": meta.get("HTTP_X_FORWARDED_PROTO"),
		"x_forwarded_for": meta.get("HTTP_X_FORWARDED_FOR"),
		"user_agent": meta.get("HTTP_USER_AGENT"),
	}
	return JsonResponse(info)


def accessibility(request):
	"""Static Accessibility Statement page."""
	return render(request, "accessibility.html")


def cutting(request):
	"""Cutting page: new standalone page with its own hero and simple content."""
	# Reuse the contact form pattern
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה, נחזור אליך בהקדם.")
			return redirect("cutting")
	else:
		form = ContactRequestForm()

	# Cutting gallery (optional): latest configured
	cut_gallery = CuttingGallery.objects.order_by("-updated", "-id").first()
	cut_images = []
	if cut_gallery:
		cut_images = [
			cut_gallery.image1,
			cut_gallery.image2,
			cut_gallery.image3,
			cut_gallery.image4,
			cut_gallery.image5,
			cut_gallery.image6,
			cut_gallery.image7,
			cut_gallery.image8,
			cut_gallery.image9,
		]

	ctx = {"contact_form": form, "cut_gallery": cut_gallery, "cut_images": cut_images}
	return render(request, "cutting.html", ctx)


def photos(request):
	"""Standalone photos gallery page managed from admin."""
	gallery = PhotosGallery.objects.order_by("-updated", "-id").first()
	images = []
	if gallery:
		images = [
			gallery.image1, gallery.image2, gallery.image3,
			gallery.image4, gallery.image5, gallery.image6,
			gallery.image7, gallery.image8, gallery.image9,
			gallery.image10, gallery.image11, gallery.image12,
		]
	ctx = {"gallery": gallery, "images": images}
	return render(request, "photos.html", ctx)
