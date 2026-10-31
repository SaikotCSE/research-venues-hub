from django.urls import path

from webapp import views as pages

app_name = "tracker"

# Pages rendered by the React app; data lives under /api/app/tracker/.
urlpatterns = [
    path("", pages.private_page("tracker_board"), name="board"),
    path("new/", pages.private_page("tracker_new"), name="create"),
    path("s/<int:pk>/", pages.submission_detail, name="detail"),
    path("papers/", pages.private_page("tracker_papers"), name="papers"),
]
