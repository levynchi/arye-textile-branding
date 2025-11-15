"""Middleware for protecting white catalog pages with HTTP Basic Authentication."""

import base64
from django.http import HttpResponse
from .models import WhiteCatalogUser


class WhiteCatalogAuthMiddleware:
	"""Middleware to protect /white-catalog/ URLs with HTTP Basic Authentication."""
	
	def __init__(self, get_response):
		self.get_response = get_response
	
	def __call__(self, request):
		# Check if the request is for a white catalog page
		if request.path.startswith('/white-catalog/'):
			# Check for authentication
			if not self._authenticate(request):
				# Return 401 with WWW-Authenticate header to trigger browser popup
				response = HttpResponse(
					'<h1>דרוש אימות</h1><p>עליך להזין שם משתמש וסיסמא תקפים כדי לגשת לקטלוג לבן.</p>',
					status=401,
					content_type='text/html; charset=utf-8'
				)
				response['WWW-Authenticate'] = 'Basic realm="Arye Textil White Catalog"'
				return response
		
		response = self.get_response(request)
		return response
	
	def _authenticate(self, request):
		"""Verify HTTP Basic Authentication credentials."""
		auth_header = request.META.get('HTTP_AUTHORIZATION', '')
		
		if not auth_header.startswith('Basic '):
			return False
		
		try:
			# Decode the base64 encoded credentials
			auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
			username, password = auth_decoded.split(':', 1)
		except (ValueError, UnicodeDecodeError):
			return False
		
		# Check credentials against WhiteCatalogUser model
		try:
			user = WhiteCatalogUser.objects.get(username=username, is_active=True)
			if user.check_password(password):
				# Store user in request for potential use in views
				request.white_catalog_user = user
				return True
		except WhiteCatalogUser.DoesNotExist:
			pass
		
		return False

