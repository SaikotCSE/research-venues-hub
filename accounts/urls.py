from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("profile/token/<str:which>/", views.regenerate_token, name="regenerate_token"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read/", views.notifications_read, name="notifications_read"),
    path("searches/save/", views.saved_search_create, name="search_save"),
    path("searches/<int:pk>/delete/", views.saved_search_delete, name="search_delete"),
    path("lists/", views.lists_index, name="lists"),
    path("lists/new/", views.list_create, name="list_create"),
    path("lists/<slug:slug>/", views.list_detail, name="list_detail"),
    path("lists/<slug:slug>/update/", views.list_update, name="list_update"),
    path("lists/<slug:slug>/toggle/<slug:venue_slug>/", views.list_toggle_venue, name="list_toggle"),
    path("calendar/<str:token>.ics", views.calendar_feed, name="calendar_feed"),
]
