from django.urls import path

from . import api, openapi, views, views_extra

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
    path("recommend/", views_extra.recommend_view, name="recommend"),
    path("plan/", views_extra.plan_view, name="plan"),
    path("insights/", views_extra.insights, name="insights"),
    path("calendar.ics", views_extra.calendar_filtered, name="calendar_filtered"),
    path("feed/deadlines.atom", views_extra.DeadlineFeed(), name="atom_feed"),
    path("api/docs/", views_extra.api_docs, name="api_docs"),
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
