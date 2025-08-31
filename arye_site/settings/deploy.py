from .base import *  # noqa

# Production-specific overrides
DEBUG = os.environ.get('DJANGO_DEBUG', 'false').lower() in ('1','true','yes','on')

# Ensure critical envs are set in deploy; provide minimal safe fallbacks/logging
if not SECRET_KEY or SECRET_KEY == 'dev-insecure-key-change-me':
    raise RuntimeError('DJANGO_SECRET_KEY must be set in production')

# In App Platform, configure DJANGO_ALLOWED_HOSTS and DJANGO_CSRF_TRUSTED_ORIGINS appropriately
# Media storage should already be S3 when AWS_* env vars exist

# Behind a proxy (DigitalOcean/Cloudflare), trust X-Forwarded-Proto for secure detection
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
