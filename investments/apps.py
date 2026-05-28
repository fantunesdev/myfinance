from django.apps import AppConfig


class InvestmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'investments'
    verbose_name = 'Investimentos'

    def ready(self):
        try:
            import investments.signals  # noqa: F401
        except Exception:
            pass
