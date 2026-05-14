from uuid import UUID

from config.celery import app
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404

import logging


logger = logging.getLogger(__name__)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def send_triaje_to_queue(self, triaje_id: str | UUID):
    """Procesa un `Triaje` y lo mueve a `EN_CONSULTORIO` si existe cola.

    Acepta `str` o `UUID` porque Celery serializa el identificador y el task
    se ejecuta tanto desde `.delay()` como desde `.run()` en pruebas.
    El lookup usa `get_object_or_404(..., pk=triaje_id)` para mantener el
    contrato de búsqueda por clave primaria.

    El task es idempotente: si la cola ya está en el estado destino, no hace
    trabajo adicional.
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

    logger.info(
        "send_triaje_to_queue started",
        extra={"triaje_id": str(triaje.pk)},
    )

    try:
        with transaction.atomic():
            try:
                cola = ColaEstado.objects.select_for_update().get(triaje=triaje)
            except ColaEstado.DoesNotExist:
                logger.warning(
                    "send_triaje_to_queue skipped: cola estado missing",
                    extra={"triaje_id": str(triaje.pk)},
                )
                return

            if cola.estado == ColaEstado.EstadoChoices.EN_CONSULTORIO:
                logger.info(
                    "send_triaje_to_queue no-op: already in consultorio",
                    extra={"triaje_id": str(triaje.pk), "estado": cola.estado},
                )
                return

            cola.set_estado(ColaEstado.EstadoChoices.EN_CONSULTORIO)
            logger.info(
                "send_triaje_to_queue transitioned",
                extra={
                    "triaje_id": str(triaje.pk),
                    "estado_anterior": ColaEstado.EstadoChoices.EN_ESPERA,
                    "estado_nuevo": ColaEstado.EstadoChoices.EN_CONSULTORIO,
                },
            )
    except Exception:
        logger.exception(
            "send_triaje_to_queue failed",
            extra={"triaje_id": str(triaje.pk)},
        )
        raise
