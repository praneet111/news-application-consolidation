from django.apps import AppConfig


class NewsAppConfig(AppConfig):
    """
    News application configuration.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "news_app"

    def ready(self):
        """
        Load signals.
        """

        from django.db.models.signals import post_migrate

        from . import signals  # noqa: F401
        from .roles import configure_role_groups

        post_migrate.connect(
            configure_role_groups,
            sender=self,
            dispatch_uid="news_app.configure_role_groups",
        )
