import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from triage.models import Triaje

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Triaje)
def triaje_post_save(sender, instance, created, **kwargs):
    if not created:
        return

    # Lazy imports to avoid circular import issues
    try:
        from medico.models import ColaEstado
        from medico.tasks import send_triaje_to_queue
    except Exception as exc:
        logger.exception(
            "triaje_post_save failed importing medico modules",
            extra={"triaje_id": str(instance.pk)},
        )
        return

    # Create ColaEstado if missing
    try:
        cola, created_cola = ColaEstado.objects.get_or_create(triaje=instance)
    except Exception as exc:
        logger.exception(
            "triaje_post_save failed creating ColaEstado",
            extra={"triaje_id": str(instance.pk)},
        )
        return

    logger.info(
        "triaje_post_save ensured ColaEstado",
        extra={"triaje_id": str(instance.pk), "cola_created": created_cola},
    )

    # Try to enqueue the Celery task; be defensive in case broker is down
    try:
        send_triaje_to_queue.delay(instance.id)
    except Exception as exc:
        logger.exception(
            "triaje_post_save failed to queue Celery task",
            extra={"triaje_id": str(instance.pk)},
        )
