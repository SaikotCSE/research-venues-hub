from django.urls import path

from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.board, name="board"),
    path("new/", views.submission_create, name="create"),
    path("s/<int:pk>/", views.submission_detail, name="detail"),
    path("s/<int:pk>/status/", views.submission_status, name="status"),
    path("s/<int:pk>/delete/", views.submission_delete, name="delete"),
    path("s/<int:pk>/checklist/add/", views.checklist_add, name="checklist_add"),
    path("s/<int:pk>/checklist/<int:item_id>/toggle/", views.checklist_toggle, name="checklist_toggle"),
    path("papers/", views.papers, name="papers"),
    path("papers/<int:pk>/delete/", views.paper_delete, name="paper_delete"),
]
