from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, ListView

from admision.models import Paciente

from .exceptions import RN01ImmutableTriageError
from .forms import TriajeForm
from .models import Triaje


class TriagePermissionMixin(PermissionRequiredMixin):
    """
    Verifica los permisos para el módulo de triage.
    Redirige a 'home' con un mensaje de error si no tiene permisos.
    """

    def handle_no_permission(self):
        messages.error(
            self.request,
            "No tiene los permisos necesarios para acceder a esta función de triaje.",
        )
        return redirect("home")


class TriajeListView(TriagePermissionMixin, ListView):
    model = Triaje
    permission_required = "triage.view_triaje"
    template_name = "triage/triage_list.html"
    context_object_name = "triajes"

    def get_queryset(self):
        # Obtener el triaje más reciente para cada paciente que esté en espera o consulta
        # Usamos una subconsulta para filtrar solo el último triaje por paciente
        from django.db.models import OuterRef, Subquery

        ultimos_triajes_ids = (
            Triaje.objects.filter(
                paciente=OuterRef("paciente"),
                cola_estado__estado__in=["EN_ESPERA", "EN_CONSULTORIO"],
            )
            .order_by("-created_at")
            .values("id")[:1]
        )

        return (
            Triaje.objects.select_related("paciente", "cola_estado")
            .filter(id__in=Subquery(ultimos_triajes_ids))
            .order_by("nivel_prioridad", "-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Verificar si hay pacientes críticos (Nivel 1 o 2) para alerta sonora
        context["any_critical"] = (
            self.get_queryset()
            .filter(nivel_prioridad__in=[1, 2], cola_estado__estado="EN_ESPERA")
            .exists()
        )
        return context

    def get_template_names(self):
        # En el poll HTMX (cada 10 s) devolvemos solo el fragmento de filas, que
        # entra por innerHTML al <tbody>. Evita anidar un <tbody> dentro de otro
        # (HTML inválido que apelmazaba las celdas a la izquierda).
        if self.request.headers.get("HX-Request"):
            return ["triage/_triage_rows.html"]
        return ["triage/triage_list.html"]


class PacienteTriajeHistoryView(TriagePermissionMixin, ListView):
    model = Triaje
    permission_required = "triage.view_triaje"
    template_name = "triage/paciente_triaje_history.html"
    context_object_name = "triajes"

    def get_queryset(self):
        self.paciente = get_object_or_404(Paciente, pk=self.kwargs["paciente_pk"])
        return Triaje.objects.filter(paciente=self.paciente).select_related(
            "cola_estado", "usuario_enfermeria"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente
        return context


class TriajeCreateView(TriagePermissionMixin, CreateView):
    model = Triaje
    form_class = TriajeForm
    permission_required = "triage.add_triaje"
    template_name = "triage/triage_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.paciente = get_object_or_404(
            Paciente, pk=kwargs["paciente_pk"], estado="activo"
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.paciente
        context[
            "title"
        ] = f"Triaje inicial: {self.paciente.nombres} {self.paciente.apellidos}"
        return context

    def form_valid(self, form):
        try:
            self.object = form.save(
                paciente=self.paciente, usuario_enfermeria=self.request.user
            )
        except RN01ImmutableTriageError as exc:
            form.add_error(None, str(exc))
            context = self.get_context_data(form=form)
            return self.render_to_response(context, status=400)

        messages.success(
            self.request,
            f"Triaje registrado con prioridad {self.object.nivel_prioridad} ({self.object.color_manchester}).",
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("admision:paciente_detail", kwargs={"pk": self.paciente.pk})

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)
