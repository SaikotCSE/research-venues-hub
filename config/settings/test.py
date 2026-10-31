"""Settings for the automated test-suite: fast, isolated and deterministic.

Uses in-memory SQLite unless DATABASE_URL is set (CI also runs the suite on PostgreSQL).
"""
import dj_database_url

from config.env import env

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-only-secret-key-6b1e9d2f4a8c0e3b5d7f9a1c3e5b7d9f0a2c4e6b8"
ALLOWED_HOSTS = ["testserver", "localhost"]
SITE_URL = "http://testserver"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DATABASES = {
    "default": dj_database_url.parse(env("DATABASE_URL")) if env("DATABASE_URL")
    else {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "venuepulse-tests"}}
RATELIMIT_ENABLED = False  # individual tests opt in with override_settings
LOGGING = {"version": 1, "disable_existing_loggers": False, "root": {"handlers": [], "level": "CRITICAL"}}
# Serve static files straight from the app directories (no collectstatic needed in tests).
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True
