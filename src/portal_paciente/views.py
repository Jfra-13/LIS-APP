from django.shortcuts import render, get_object_or_404
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
from admision.models import Paciente
from consulta.models import NotaMedica
from .forms import PatientLoginForm

class PatientRequiredMixin(UserPassesTestMixin):
    """Asegura que el usuario sea un paciente y solo acceda a sus datos."""
    def test_func(self):
        # El usuario debe estar autenticado y existir como paciente con ese DNI
        return Paciente.objects.filter(dni=self.request.user.username).exists()

class PatientLoginView(LoginView):
    template_name = 'portal_paciente/login.html'
    authentication_form = PatientLoginForm

class PatientDashboardView(LoginRequiredMixin, PatientRequiredMixin, ListView):
    model = NotaMedica
    template_name = 'portal_paciente/dashboard.html'
    context_object_name = 'notas'

    def get_queryset(self):
        # Filtrar notas por el DNI del usuario autenticado
        return NotaMedica.objects.filter(paciente__dni=self.request.user.username).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['paciente'] = get_object_or_404(Paciente, dni=self.request.user.username)
        return context

class RecetaDetailView(LoginRequiredMixin, PatientRequiredMixin, DetailView):
    model = NotaMedica
    template_name = 'portal_paciente/receta_detail.html'
    context_object_name = 'nota'

    def get_object(self, queryset=None):
        # Asegurar que la nota pertenezca al paciente por DNI
        return get_object_or_404(NotaMedica, receta_id=self.kwargs.get('receta_id'), paciente__dni=self.request.user.username)
