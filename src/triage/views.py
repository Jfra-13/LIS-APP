from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView

from admision.models import Paciente

from .exceptions import RN01ImmutableTriageError
from .forms import TriajeForm
from .models import Triaje


class EnfermeriaRequiredMixin(UserPassesTestMixin):
    """Restringe el modulo de triaje al grupo Enfermeria."""

    def test_func(self):
        return self.request.user.groups.filter(name="Enfermeria").exists()

    def handle_no_permission(self):
        messages.error(
            self.request, "Solo el personal de Enfermeria puede registrar triajes."
        )
        return redirect("home")


class TriajeCreateView(EnfermeriaRequiredMixin, CreateView):
    model = Triaje
    form_class = TriajeForm
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
