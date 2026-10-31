from django.urls import path

from . import views

app_name = "venues"

urlpatterns = [
    path("", views.venue_list, name="list"),
    path("venue/<slug:slug>/", views.venue_detail, name="detail"),
    path("venue/<slug:slug>/modal/", views.venue_modal, name="modal"),
    path("venue/<slug:slug>/ics/", views.venue_ics, name="ics"),
    path("venue/<slug:slug>/bookmark/", views.toggle_bookmark, name="bookmark"),
    path("venue/<slug:slug>/note/", views.save_note, name="note"),
    path("compare/", views.compare, name="compare"),
    path("targets/", views.targets, name="targets"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("export/json/", views.export_json, name="export_json"),
    path("api/venues/", views.api_venues, name="api_venues"),
    path("api/venues/<slug:slug>/", views.api_venue_detail, name="api_venue_detail"),
    path("api/tags/", views.api_tags, name="api_tags"),
    path("api/stats/", views.api_stats, name="api_stats"),
]
