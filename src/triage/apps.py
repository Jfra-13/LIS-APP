from django.apps import AppConfig

class TriageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'triage'

    def ready(self):
        # Importamos las señales cuando la app arranca
        import triage.signals