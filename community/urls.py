from django.urls import path

from webapp import views as pages

app_name = "community"

urlpatterns = [
    path("changes/", pages.simple_page("radar"), name="changes"),
]
