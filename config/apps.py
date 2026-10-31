from django.apps import AppConfig


class ConfigConfig(AppConfig):
    """Registers project-level system checks."""

    name = "config"
    verbose_name = "Project configuration"

    def ready(self):
        from . import checks  # noqa: F401
