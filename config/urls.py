from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.decorators.cache import cache_page

from config import views
from config.sitemaps import SITEMAPS

admin.site.site_header = "VenuePulse administration"
admin.site.site_title = "VenuePulse admin"
admin.site.index_title = "Catalogue, community & users"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("healthz", views.healthz, name="healthz"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("about/", views.about, name="about"),
    path("privacy/", views.privacy, name="privacy"),
    path("sitemap.xml", cache_page(60 * 60)(sitemap), {"sitemaps": SITEMAPS}, name="sitemap"),
    path("accounts/", include("accounts.urls")),
    path("tracker/", include("tracker.urls")),
    path("community/", include("community.urls")),
    path("", include("venues.urls")),
]
