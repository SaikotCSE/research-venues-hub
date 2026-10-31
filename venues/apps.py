from django.apps import AppConfig


class VenuesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "venues"
    verbose_name = "Venues & deadlines"

    def ready(self):
        from . import signals  # noqa: F401
