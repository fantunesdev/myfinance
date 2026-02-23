from django.apps import AppConfig


class StatementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'statement'

    def ready(self):
        # Import signals to ensure they are registered
        try:
            import statement.signals  # noqa: F401
        except Exception:
            pass
