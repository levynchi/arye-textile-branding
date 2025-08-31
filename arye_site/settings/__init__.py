"""
Settings package. Use one of:
 - arye_site.settings.local
 - arye_site.settings.deploy

Keep this file minimal; real settings live in base/local/deploy.
"""
# Default to base settings when importing `arye_site.settings`.
# Override by using DJANGO_SETTINGS_MODULE=arye_site.settings.local or .deploy
from .base import *  # noqa
