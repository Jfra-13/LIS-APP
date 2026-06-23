from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import PacienteForm
from .models import Paciente


class AdmisionPermissionMixin(PermissionRequiredMixin):
    """
    Verifica los permisos para el módulo de admisión.

    Usa el comportamiento estándar de Django (AccessMixin):
    - Usuario anónimo: redirección a login (302).
    - Usuario autenticado sin permiso: 403 Forbidden renderizado en contexto
      (handler403 global), sin sacarlo de donde estaba.
    """

    pass


class PacienteListView(AdmisionPermissionMixin, ListView):
    """Vista para listar pacientes activos."""

    model = Paciente
    permission_required = "admision.view_paciente"
    template_name = "admision/paciente_list.html"
    context_object_name = "pacientes"
    paginate_by = 50

    def get_queryset(self):
        """
        Retorna pacientes activos con select_related.
        Permite búsqueda por DNI o nombres.
        """
        # Delegar búsqueda al manager para consistencia
        search = self.request.GET.get("search", "").strip()
        return Paciente.objects.search(search)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        return context

    def render_to_response(self, context, **response_kwargs):
        """Return only the table-rows partial for HTMX requests."""
        if self.request.headers.get("HX-Request"):
            from django.template.response import TemplateResponse

            return TemplateResponse(
                self.request,
                "admision/_paciente_rows.html",
                context,
            )
        return super().render_to_response(context, **response_kwargs)


class PacienteCreateView(AdmisionPermissionMixin, CreateView):
    """Vista para crear un nuevo paciente."""

    model = Paciente
    form_class = PacienteForm
    permission_required = "admision.add_paciente"
    template_name = "admision/paciente_form.html"

    def form_valid(self, form):
        """Asignar usuario_creador antes de guardar."""
        form.instance.usuario_creador = self.request.user
        try:
            response = super().form_valid(form)
        except IntegrityError:
            # Capturar race condition sobre unique DNI y transformar a error de formulario
            form.add_error("dni", "Ya existe un paciente con este DNI.")
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Paciente {form.instance.nombres} {form.instance.apellidos} creado exitosamente.",
        )
        return response

    def get_success_url(self):
        return reverse_lazy("admision:paciente_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Crear Nuevo Paciente"
        context["button_text"] = "Crear Paciente"
        return context


class PacienteDetailView(AdmisionPermissionMixin, DetailView):
    """Vista para ver detalles de un paciente."""

    model = Paciente
    permission_required = "admision.view_paciente"
    template_name = "admision/paciente_detail.html"
    context_object_name = "paciente"

    def get_queryset(self):
        """Optimizar query con select_related."""
        return Paciente.objects.select_related("usuario_creador")


class PacienteUpdateView(AdmisionPermissionMixin, UpdateView):
    """Vista para editar un paciente existente."""

    model = Paciente
    form_class = PacienteForm
    permission_required = "admision.change_paciente"
    template_name = "admision/paciente_form.html"

    def form_valid(self, form):
        """No permitir cambiar usuario_creador."""
        try:
            response = super().form_valid(form)
        except IntegrityError:
            form.add_error("dni", "Ya existe un paciente con este DNI.")
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Paciente {form.instance.nombres} {form.instance.apellidos} actualizado exitosamente.",
        )
        return response

    def get_success_url(self):
        return reverse_lazy("admision:paciente_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[
            "title"
        ] = f"Editar Paciente: {self.object.nombres} {self.object.apellidos}"
        context["button_text"] = "Actualizar Paciente"
        return context


class PacienteDeleteView(AdmisionPermissionMixin, DeleteView):
    """Vista para eliminar un paciente (soft delete)."""

    model = Paciente
    permission_required = "admision.delete_paciente"
    template_name = "admision/paciente_confirm_delete.html"
    success_url = reverse_lazy("admision:paciente_list")

    def post(self, request, *args, **kwargs):
        """Realizar soft delete en lugar de eliminar fila."""
        self.object = self.get_object()
        paciente_str = f"{self.object.nombres} {self.object.apellidos}"

        # Soft delete delegado al modelo
        try:
            self.object.soft_delete()
        except Exception:
            messages.error(request, "No se pudo eliminar el paciente. Intente de nuevo.")
            return redirect(self.success_url)

        messages.success(
            request, f"Paciente {paciente_str} marcado como inactivo correctamente."
        )
        return redirect(self.success_url)
