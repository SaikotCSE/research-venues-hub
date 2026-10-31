from django.contrib.auth import views as auth_views
from django.urls import path

from config.ratelimit import ratelimit

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", ratelimit("login")(views.SignInView.as_view()), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    # password management
    path("password/reset/", ratelimit("password_reset")(views.PasswordResetView.as_view()), name="password_reset"),
    path("password/reset/sent/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    # dashboard, profile & settings
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("profile/token/<str:which>/", views.regenerate_token, name="regenerate_token"),
    path("preferences/timezone/", views.set_timezone, name="set_timezone"),
    path("settings/", views.account_settings, name="settings"),
    path("settings/export/", views.export_data, name="export_data"),
    path("settings/delete/", views.delete_account, name="delete_account"),
    # notifications & saved searches
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/read/", views.notifications_read, name="notifications_read"),
    path("searches/save/", views.saved_search_create, name="search_save"),
    path("searches/<int:pk>/delete/", views.saved_search_delete, name="search_delete"),
    # venue lists
    path("lists/", views.lists_index, name="lists"),
    path("lists/new/", views.list_create, name="list_create"),
    path("lists/<slug:slug>/", views.list_detail, name="list_detail"),
    path("lists/<slug:slug>/update/", views.list_update, name="list_update"),
    path("lists/<slug:slug>/toggle/<slug:venue_slug>/", views.list_toggle_venue, name="list_toggle"),
    # private calendar feed
    path("calendar/<str:token>.ics", views.calendar_feed, name="calendar_feed"),
]
