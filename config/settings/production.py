"""Production settings: secure by default. Every secret comes from the environment."""
from django.core.exceptions import ImproperlyConfigured

from config.env import env, env_bool, env_int

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [r"^healthz/?$"]
# Only disable for plain-HTTP local smoke tests (e.g. docker compose on localhost).
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", True)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365
