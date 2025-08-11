from django.shortcuts import render
from django.contrib import messages
from .models import Gallery, Banner, ContactRequest
from .forms import ContactRequestForm


def home(request):
	gallery = Gallery.objects.order_by('-updated').first()
	banner = Banner.objects.order_by('-updated').first()
	if request.method == "POST":
		form = ContactRequestForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, "ההודעה נשלחה בהצלחה!")
			form = ContactRequestForm()  # reset
	else:
		form = ContactRequestForm()
	return render(request, 'home.html', {"gallery": gallery, "banner": banner, "contact_form": form})
