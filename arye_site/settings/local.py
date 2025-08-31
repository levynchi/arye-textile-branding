from .base import *  # noqa

# Local developer defaults
DEBUG = True

# Allow all hosts locally unless explicitly set
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Explicitly allow HTTP origins for CSRF during local development
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']

# Do not force HTTPS in local dev
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_PROXY_SSL_HEADER = None
