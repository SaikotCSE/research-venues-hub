"""Settings shared by every environment. Environment-specific modules import * from here."""
from pathlib import Path

import dj_database_url

from config.env import env, env_bool, env_int, env_list, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", [])
SITE_URL = env("SITE_URL").rstrip("/")  # absolute base for emails/feeds; falls back to the request host
ADMIN_URL = env("DJANGO_ADMIN_URL", "admin/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "django.forms",
    "config",
    "venues",
    "accounts",
    "tracker",
    "community",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "config.middleware.RequestIDMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
FORM_RENDERER = "config.forms.FormRenderer"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.nav",
            ],
            "builtins": ["venues.templatetags.venue_extras"],
        },
    },
]

# Database: DATABASE_URL (e.g. postgres://user:pass@host:5432/db); SQLite by default.
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=env_int("DB_CONN_MAX_AGE", 60),
        conn_health_checks=True,
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache: Redis when REDIS_URL is set, otherwise per-process memory.
if env("REDIS_URL"):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": env("REDIS_URL"), "KEY_PREFIX": "vp"}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "venuepulse"}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "venues:list"
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24  # 1 day

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

SESSION_COOKIE_AGE = 60 * 60 * 24 * 365  # anonymous bookmarks live in the session for a year
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Email: SMTP when EMAIL_HOST is set, console otherwise.
if env("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env_int("EMAIL_PORT", 587)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
    EMAIL_TIMEOUT = 15
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DJANGO_FROM_EMAIL", "VenuePulse <noreply@venuepulse.local>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Content-Security-Policy (see config/middleware.py). Alpine.js evaluates expressions, hence 'unsafe-eval'.
CSP_ENABLED = env_bool("CSP_ENABLED", True)
CSP_REPORT_ONLY = env_bool("CSP_REPORT_ONLY", False)
CSP_DIRECTIVES = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'unsafe-eval'", "{nonce}"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:"],
    "font-src": ["'self'"],
    "connect-src": ["'self'"],
    "frame-ancestors": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "object-src": ["'none'"],
}
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"

# Rate limits: "<count>/<s|m|h|d>" per client (see config/ratelimit.py).
RATELIMIT_ENABLED = env_bool("RATELIMIT_ENABLED", True)
RATELIMIT_USE_X_FORWARDED_FOR = env_bool("RATELIMIT_USE_X_FORWARDED_FOR", False)
RATELIMITS = {
    "login": "10/m",
    "signup": "5/h",
    "password_reset": "5/h",
    "community_write": "30/h",
    "api_public": "300/m",
    "api_token": "120/m",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "config.logging.RequestIDFilter"}},
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s [%(name)s] [req:%(request_id)s] %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard", "filters": ["request_id"]},
        "null": {"class": "logging.NullHandler"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        # Scanners hammer servers with bogus Host headers; the 400 response is enough.
        "django.security.DisallowedHost": {"handlers": ["null"], "propagate": False},
        "venuepulse": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO"), "propagate": False},
    },
}
