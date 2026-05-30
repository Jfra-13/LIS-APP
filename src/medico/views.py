from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, View
from .models import ColaEstado


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
                request, f"Paciente {cola_item.triaje.paciente.dni} llamado a consultorio."
            )
        except ValueError as e:
            messages.error(request, str(e))

        return redirect("medico:cola_atencion")
