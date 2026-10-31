"""Routes for the session-authenticated JSON API used by the React app (mounted at /api/app/)."""

from django.urls import path

from . import account, catalog, community, session, tracker

app_name = "app_api"

urlpatterns = [
    # session & authentication
    path("session/", session.session, name="session"),
    path("auth/login/", session.login_view, name="login"),
    path("auth/logout/", session.logout_view, name="logout"),
    path("auth/signup/", session.signup, name="signup"),
    path("auth/password-reset/", session.password_reset, name="password_reset"),
    path("auth/password-reset/confirm/", session.password_reset_confirm, name="password_reset_confirm"),
    path("auth/password-change/", session.password_change, name="password_change"),
    path("auth/verify-email/resend/", session.resend_verification, name="resend_verification"),
    # catalogue
    path("facets/", catalog.facets, name="facets"),
    path("home/", catalog.home, name="home"),
    path("explore/", catalog.explore, name="explore"),
    path("explore/timeline/", catalog.explore_timeline, name="explore_timeline"),
    path("explore/calendar/", catalog.explore_calendar, name="explore_calendar"),
    path("venues/<slug:slug>/", catalog.venue_detail, name="venue"),
    path("venues/<slug:slug>/star/", catalog.venue_star, name="venue_star"),
    path("venues/<slug:slug>/note/", catalog.venue_note, name="venue_note"),
    path("venues/<slug:slug>/review/", community.review, name="venue_review"),
    path("cycles/<int:cycle_id>/suggestions/", community.suggest, name="suggest"),
    path("suggestion-fields/", community.suggestion_fields, name="suggestion_fields"),
    path("targets/", catalog.targets, name="targets"),
    path("compare/", catalog.compare, name="compare"),
    path("recommend/", catalog.recommend_view, name="recommend"),
    path("plan/", catalog.plan_view, name="plan"),
    path("radar/", catalog.radar, name="radar"),
    path("venue-options/", catalog.venue_options, name="venue_options"),
    path("api-meta/", catalog.api_meta, name="api_meta"),
    path("timezones/", account.timezones, name="timezones"),
    # signed-in user
    path("me/dashboard/", account.dashboard, name="dashboard"),
    path("me/profile/", account.profile, name="profile"),
    path("me/tokens/<str:which>/", account.regenerate_token, name="regenerate_token"),
    path("me/timezone/", account.set_timezone, name="set_timezone"),
    path("me/email/", account.change_email, name="change_email"),
    path("me/delete/", account.delete_account, name="delete_account"),
    path("me/notifications/", account.notifications, name="notifications"),
    path("me/notifications/read/", account.notifications_read, name="notifications_read"),
    path("me/searches/", account.saved_searches, name="saved_searches"),
    path("me/searches/<int:pk>/", account.saved_search_delete, name="saved_search"),
    path("lists/", account.lists, name="lists"),
    path("lists/<slug:slug>/", account.list_detail, name="list"),
    path("lists/<slug:slug>/venues/<slug:venue_slug>/", account.list_toggle, name="list_toggle"),
    # tracker
    path("tracker/board/", tracker.board, name="board"),
    path("tracker/submissions/", tracker.submissions, name="submissions"),
    path("tracker/submissions/<int:pk>/", tracker.submission, name="submission"),
    path("tracker/submissions/<int:pk>/checklist/", tracker.checklist_add, name="checklist_add"),
    path("tracker/submissions/<int:pk>/checklist/<int:item_id>/", tracker.checklist_item, name="checklist_item"),
    path("tracker/papers/", tracker.papers, name="papers"),
    path("tracker/papers/<int:pk>/", tracker.paper, name="paper"),
]
