from django.views.generic import TemplateView, ListView, UpdateView, CreateView
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from .models import RegistroTriage


# Si tienes un modelo Paciente, asegúrate de importarlo:
# from .models import Paciente

# ==========================================
# 1. VISTAS GENERALES Y RUTEO
# ==========================================
class CustomLoginView(LoginView):
    template_name = 'triage/login.html'
    redirect_authenticated_user = True


class DashboardRouterView(LoginRequiredMixin, TemplateView):
    template_name = 'triage/dashboard.html'
    # Nota para el MVP: Más adelante aquí agregaremos la lógica que
    # lea el rol del usuario y lo redirija automáticamente a su módulo.


# ==========================================
# 2. MÓDULO DE ADMISIÓN (Técnico Administrativo)
# ==========================================
class PacienteListaCreateView(LoginRequiredMixin, TemplateView):
    template_name = 'triage/admision/lista_pacientes.html'
    # Aquí irá la lógica para buscar DNI y listar pacientes


class GenerarTicketView(LoginRequiredMixin, CreateView):
    model = RegistroTriage
    template_name = 'triage/admision/generar_ticket.html'
    fields = ['paciente']  # Solo creamos el ticket asociando al paciente
    success_url = reverse_lazy('dashboard')


# ==========================================
# 3. MÓDULO DE TRIAJE (Enfermería)
# ==========================================
class ColaTriajeListView(LoginRequiredMixin, ListView):
    model = RegistroTriage
    template_name = 'triage/enfermeria/cola_triaje.html'
    context_object_name = 'triages'

    def get_queryset(self):
        # Filtramos solo los que no tienen nivel asignado
        return RegistroTriage.objects.filter(nivel_asignado__isnull=True).order_by('fecha_ingreso')


class EvaluacionTriajeUpdateView(LoginRequiredMixin, UpdateView):
    model = RegistroTriage
    template_name = 'triage/enfermeria/evaluar_paciente.html'
    fields = ['saturacion_oxigeno', 'frecuencia_cardiaca', 'temperatura']
    success_url = reverse_lazy('cola_triaje')
    # Al guardar, el modelo automáticamente llamará a Mánchester gracias al MVP anterior


# ==========================================
# 4. MÓDULO MÉDICO (Especialista Tópico)
# ==========================================
class ColaMedicaListView(LoginRequiredMixin, ListView):
    model = RegistroTriage
    template_name = 'triage/medico/cola_medica.html'
    context_object_name = 'triages'

    def get_queryset(self):
        # Filtramos los que ya tienen nivel, pero no han sido procesados/atendidos
        # Y los ORDENAMOS por nivel de gravedad (Mánchester)
        return RegistroTriage.objects.filter(
            nivel_asignado__isnull=False,
            procesado_por_ia=False
        ).order_by('nivel_asignado', 'fecha_ingreso')


class AtencionMedicaUpdateView(LoginRequiredMixin, UpdateView):
    model = RegistroTriage
    template_name = 'triage/medico/atencion_medica.html'
    fields = ['notas_medico']
    success_url = reverse_lazy('cola_medica')