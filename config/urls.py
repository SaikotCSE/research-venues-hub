from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("tracker/", include("tracker.urls")),
    path("community/", include("community.urls")),
    path("", include("venues.urls")),
]
