from django.shortcuts import render
from .models import Gallery, Banner


def home(request):
	gallery = Gallery.objects.order_by('-updated').first()
	banner = Banner.objects.order_by('-updated').first()
	return render(request, 'home.html', {"gallery": gallery, "banner": banner})
