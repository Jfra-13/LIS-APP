import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class TriageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "triage"
    verbose_name = "Modulo de Triaje"

    def ready(self):
        # Import signals to register post_save hooks
        try:
            from . import signals  # noqa: F401
        except Exception:
            logger.exception("Failed to import triage signals")
