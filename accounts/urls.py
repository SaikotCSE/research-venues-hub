from django.contrib.auth import views as auth_views
from django.urls import path

from webapp import views as pages

from . import views

app_name = "accounts"

urlpatterns = [
    # authentication pages (React); the forms post to /api/app/auth/* (sign-up and reset use emailed codes)
    path("login/", pages.guest_page("login"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", pages.guest_page("signup"), name="signup"),
    path("password/reset/", pages.guest_page("password_reset"), name="password_reset"),
    path("password/reset/complete/", pages.guest_page("password_reset_complete"), name="password_reset_complete"),
    path("password/change/", pages.private_page("password_change"), name="password_change"),
    path("verify/<str:token>/", views.verify_email, name="verify_email"),
    # signed-in pages (React)
    path("", pages.private_page("dashboard"), name="dashboard"),
    path("profile/", pages.private_page("profile"), name="profile"),
    path("settings/", pages.private_page("settings"), name="settings"),
    path("notifications/", pages.private_page("notifications"), name="notifications"),
    path("lists/", pages.private_page("lists"), name="lists"),
    path("lists/<slug:slug>/", pages.list_detail, name="list_detail"),
    # downloads & feeds
    path("settings/export/", views.export_data, name="export_data"),
    path("lists/<slug:slug>/calendar.ics", views.list_calendar, name="list_calendar"),
    path("calendar/<str:token>.ics", views.calendar_feed, name="calendar_feed"),
]
