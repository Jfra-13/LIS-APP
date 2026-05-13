from config.celery import app
from django.db import transaction
from django.shortcuts import get_object_or_404


@app.task(bind=True)
def send_triaje_to_queue(self, triaje_id: int):
    """Task executed by the worker to perform initial processing of a Triaje.

    For MVP behavior this will transition the corresponding ColaEstado
    to EN_CONSULTORIO to simulate assigning the case to a medico.
    """
    # Import locally to avoid circular imports at module import time
    from medico.models import ColaEstado
    from triage.models import Triaje

    triaje = get_object_or_404(Triaje, pk=triaje_id)

    # Ensure transition happens in a transaction for consistency
    try:
        cola = ColaEstado.objects.select_for_update().get(triaje=triaje)
    except ColaEstado.DoesNotExist:
        # Nothing to do if no ColaEstado exists
        return

    with transaction.atomic():
        try:
            cola.set_estado(ColaEstado.EstadoChoices.EN_CONSULTORIO)
        except Exception as exc:
            # Re-raise to allow Celery retry policies if needed
            raise
