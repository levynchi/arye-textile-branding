"""Middleware for protecting catalog pages with HTTP Basic Authentication."""

import base64
from django.http import HttpResponse
from .models import CatalogUser


class CatalogAuthMiddleware:
	"""Middleware to protect /catalog/ URLs with HTTP Basic Authentication."""
	
	def __init__(self, get_response):
		self.get_response = get_response
	
	def __call__(self, request):
		# Check if the request is for a catalog page
		if request.path.startswith('/catalog/'):
			print(f"[CatalogAuthMiddleware] Checking auth for: {request.path}")
			# Check for authentication
			if not self._authenticate(request):
				print("[CatalogAuthMiddleware] Authentication failed - sending 401")
				# Return 401 with WWW-Authenticate header to trigger browser popup
				response = HttpResponse(
					'<h1>דרוש אימות</h1><p>עליך להזין שם משתמש וסיסמא תקפים כדי לגשת לקטלוג.</p>',
					status=401,
					content_type='text/html; charset=utf-8'
				)
				response['WWW-Authenticate'] = 'Basic realm="Arye Textil Catalog"'
				return response
			print("[CatalogAuthMiddleware] Authentication successful")
		
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
		
		# Check credentials against CatalogUser model
		try:
			user = CatalogUser.objects.get(username=username, is_active=True)
			if user.check_password(password):
				# Store user in request for potential use in views
				request.catalog_user = user
				return True
		except CatalogUser.DoesNotExist:
			pass
		
		return False

