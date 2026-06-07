import time

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count, Max
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, View
from .models import ColaEstado

# Intervalo del tick server-side que detecta cambios en la cola para SSE.
# No es el lag de entrega: si la cola cambia, el siguiente tick lo empuja.
COLA_STREAM_POLL_SECONDS = 2.0


class MedicoPermissionMixin(PermissionRequiredMixin):
    """
    Verifica los permisos para el módulo de médico.
    Redirige a 'home' con un mensaje de error si no tiene permisos.
    """

    def handle_no_permission(self):
        messages.error(self.request, "Acceso restringido a personal médico.")
        return redirect("home")


class ColaAtencionListView(MedicoPermissionMixin, ListView):
    model = ColaEstado
    permission_required = "medico.view_colaestado"
    template_name = "medico/cola_list.html"
    context_object_name = "pacientes_cola"

    def get_queryset(self):
        return (
            ColaEstado.objects.select_related("triaje", "triaje__paciente")
            .filter(
                estado__in=[
                    ColaEstado.EstadoChoices.EN_ESPERA,
                    ColaEstado.EstadoChoices.EN_CONSULTORIO,
                ]
            )
            .order_by("triaje__nivel_prioridad", "created_at")
        )


class LlamarPacienteView(MedicoPermissionMixin, View):
    permission_required = "medico.change_colaestado"

    def post(self, request, pk):
        cola_item = get_object_or_404(ColaEstado, pk=pk)
        try:
            cola_item.set_estado(ColaEstado.EstadoChoices.EN_CONSULTORIO)
            messages.success(
                request,
                f"Paciente {cola_item.triaje.paciente.dni} llamado a consultorio.",
            )
        except ValueError as e:
            messages.error(request, str(e))

        return redirect("medico:cola_atencion")


def _cola_signature() -> str:
    """Firma barata del estado visible de la cola.

    Combina la cantidad de items en cola con el `updated_at` más reciente. Si
    entra un triaje, cambia un estado o se llama a un paciente, la firma cambia
    y el stream emite un evento. Evita transmitir el fragmento completo en cada
    tick: el cliente re-pide la tabla solo cuando algo cambió.
    """
    agg = ColaEstado.objects.filter(
        estado__in=[
            ColaEstado.EstadoChoices.EN_ESPERA,
            ColaEstado.EstadoChoices.EN_CONSULTORIO,
        ]
    ).aggregate(n=Count("id"), last=Max("updated_at"))
    return f"{agg['n']}:{agg['last']}"


def _cola_event_stream():
    """Generador SSE síncrono: emite `cola-update` cuando la firma cambia.

    Síncrono a propósito: el runtime actual es WSGI (`runserver`/gunicorn) y un
    iterador async no se sirve sobre WSGI. Bajo WSGI cada conexión SSE mantiene
    ocupado un thread/worker mientras dura. Deuda Fase 4: para escalar muchas
    conexiones, servir bajo ASGI o con workers async (gevent/uvicorn).
    """
    last_signature = None
    while True:
        signature = _cola_signature()
        if signature != last_signature:
            last_signature = signature
            yield f"event: cola-update\ndata: {signature}\n\n"
        time.sleep(COLA_STREAM_POLL_SECONDS)


@permission_required("medico.view_colaestado", raise_exception=True)
def cola_stream(request):
    """Endpoint SSE de la cola de atención (`text/event-stream`)."""
    response = StreamingHttpResponse(
        _cola_event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    # Desactiva el buffering de proxies (nginx) para que el push llegue al toque.
    response["X-Accel-Buffering"] = "no"
    return response
