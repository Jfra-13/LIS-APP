from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


@receiver(post_save)
def triaje_post_save(sender, instance, created, **kwargs):
    """Generic post_save handler that reacts only to Triaje creations.

    Behavior:
    - If a Triaje is created, ensure a ColaEstado exists and enqueue a Celery task.
    - Make the handler defensive: failures queuing the task must not raise.
    """
    # Avoid importing heavy models at module import time
    try:
        from triage.models import Triaje
    except Exception:
        return

    if sender is not Triaje:
        return

    if not created:
        return

    # Lazy imports to avoid circular import issues
    try:
        from medico.models import ColaEstado
        from medico.tasks import send_triaje_to_queue
    except Exception as exc:
        logger.exception("Failed importing medico modules in signal: %s", exc)
        return

    # Create ColaEstado if missing
    try:
        cola, _ = ColaEstado.objects.get_or_create(triaje=instance)
    except Exception as exc:
        logger.exception(
            "Failed creating ColaEstado for triaje %s: %s", instance.pk, exc
        )
        return

    # Try to enqueue the Celery task; be defensive in case broker is down
    try:
        send_triaje_to_queue.delay(instance.id)
    except Exception as exc:
        logger.warning("Failed to queue triaje %s: %s", instance.pk, exc)
