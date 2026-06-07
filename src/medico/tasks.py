from uuid import UUID

from config.celery import app
from django.http import Http404
from django.shortcuts import get_object_or_404

import logging


logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_triaje_to_queue(self, triaje_id: str | UUID):
    """Garantiza, de forma idempotente, que el `Triaje` esté en la cola de espera.

    El task NO avanza el estado a `EN_CONSULTORIO`: esa transición es decisión
    manual del médico ("Llamar paciente"). Su único trabajo es asegurar que
    exista el `ColaEstado` en `EN_ESPERA`, reforzando la creación hecha por el
    signal `triaje_post_save` y haciéndola resiliente a reintentos del broker.

    Acepta `str` o `UUID` porque Celery serializa el identificador y el task se
    ejecuta tanto desde `.delay()` como desde `.run()` en pruebas. El lookup usa
    `get_object_or_404(..., pk=triaje_id)` para mantener el contrato de búsqueda
    por clave primaria.
    """
    # Import locally to avoid circular imports at module import time
    from medico.models import ColaEstado
    from triage.models import Triaje

    try:
        triaje = get_object_or_404(Triaje, pk=triaje_id)
    except Http404:
        logger.warning(
            "send_triaje_to_queue skipped: triaje not found",
            extra={"triaje_id": str(triaje_id)},
        )
        return

    cola, created = ColaEstado.objects.get_or_create(
        triaje=triaje,
        defaults={"estado": ColaEstado.EstadoChoices.EN_ESPERA},
    )
    logger.info(
        "send_triaje_to_queue ensured queue entry",
        extra={
            "triaje_id": str(triaje.pk),
            "cola_created": created,
            "estado": cola.estado,
        },
    )
