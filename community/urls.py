from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("venue/<slug:slug>/review/", views.review_save, name="review"),
    path("cycle/<int:cycle_id>/suggest/", views.suggest, name="suggest"),
    path("changes/", views.changes, name="changes"),
]
