from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Banner, Gallery, Slide
from .forms import ContactRequestForm


def home(request):
	# Content blocks
	banner = Banner.objects.order_by("-updated", "-id").first()
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
		"banner": banner,
		"gallery": gallery,
		"slides": slides_loop,
		"contact_form": form,
	}
	return render(request, "home.html", ctx)
