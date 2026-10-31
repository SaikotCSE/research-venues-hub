from django.urls import path

from webapp import views as pages

from . import api, openapi, views

app_name = "venues"

urlpatterns = [
    # pages rendered by the React app (the shell view sets status codes and SEO metadata)
    path("", pages.explore, name="list"),
    path("venue/<slug:slug>/", pages.venue_detail, name="detail"),
    path("compare/", pages.simple_page("compare"), name="compare"),
    path("targets/", pages.simple_page("targets"), name="targets"),
    path("recommend/", pages.simple_page("recommend"), name="recommend"),
    path("plan/", pages.simple_page("plan"), name="plan"),
    path("insights/", pages.simple_page("insights"), name="insights"),
    path("api/docs/", pages.simple_page("api_docs"), name="api_docs"),
    # calendars, feeds, exports, widget
    path("venue/<slug:slug>/ics/", views.venue_ics, name="ics"),
    path("embed/venue/<slug:slug>/", views.venue_embed, name="embed"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("export/json/", views.export_json, name="export_json"),
    path("calendar.ics", views.calendar_filtered, name="calendar_filtered"),
    path("feed/deadlines.atom", views.DeadlineFeed(), name="atom_feed"),
    # public & token JSON API
    path("api/openapi.json", openapi.openapi_schema, name="openapi"),
    path("api/insights/", api.insights, name="api_insights"),
    path("api/suggest/", api.suggest, name="api_suggest"),
    path("api/v1/me/", api.me, name="api_me"),
    path("api/v1/me/targets/", api.me_targets, name="api_me_targets"),
    path("api/v1/me/targets/<slug:slug>/", api.me_target_delete, name="api_me_target_delete"),
    path("api/v1/me/submissions/", api.me_submissions, name="api_me_submissions"),
    path("api/venues/", api.venues, name="api_venues"),
    path("api/venues/<slug:slug>/", api.venue_detail, name="api_venue_detail"),
    path("api/tags/", api.tags, name="api_tags"),
    path("api/stats/", api.stats, name="api_stats"),
]
