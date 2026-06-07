from uuid import UUID

from config.celery import app
from django.http import Http404
from django.shortcuts import get_object_or_404

import logging


logger = logging.getLogger(__name__)


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_clinical_note(self, nota_id: str | UUID):
    """Analiza una `NotaMedica` en segundo plano y persiste sugerencias CIE-10.

    Acepta `str` o `UUID` porque Celery serializa el identificador. El task es
    idempotente: recalcular sobre la misma nota reescribe las sugerencias sin
    efectos colaterales.

    Importante: escribe en `cie_suggestions` (propuesta de la IA), NUNCA en
    `cie_code` (diagnóstico confirmado por el médico). Usa `.update()` para
    evitar `full_clean()` y no pisar la selección manual del médico.
    """
    # Import local para evitar imports circulares al cargar el módulo
    from .models import NotaMedica
    from .services.suggestion_engine import suggest_cie

    try:
        nota = get_object_or_404(NotaMedica, pk=nota_id)
    except Http404:
        logger.warning(
            "process_clinical_note skipped: nota not found",
            extra={"nota_id": str(nota_id)},
        )
        return

    logger.info("process_clinical_note started", extra={"nota_id": str(nota.pk)})

    NotaMedica.objects.filter(pk=nota.pk).update(estado_ia=NotaMedica.EstadoIA.PROCESANDO)

    try:
        text = f"{nota.motivo_consulta} {nota.contenido}".strip()
        suggestions = suggest_cie(text, limit=5)
        NotaMedica.objects.filter(pk=nota.pk).update(
            cie_suggestions=suggestions,
            estado_ia=NotaMedica.EstadoIA.LISTO,
        )
        logger.info(
            "process_clinical_note done",
            extra={"nota_id": str(nota.pk), "count": len(suggestions)},
        )
    except Exception:
        logger.exception(
            "process_clinical_note failed",
            extra={"nota_id": str(nota.pk)},
        )
        NotaMedica.objects.filter(pk=nota.pk).update(estado_ia=NotaMedica.EstadoIA.ERROR)
        raise
