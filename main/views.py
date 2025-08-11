from django.shortcuts import render


def home(request):
	# רינדור הדף הראשי עם הטקסט אריה
	return render(request, 'home.html')
