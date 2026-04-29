from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    # General
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.DashboardRouterView.as_view(), name='dashboard'),

    # Admisión
    path('admision/pacientes/', views.PacienteListaCreateView.as_view(), name='lista_pacientes'),
    path('admision/ticket/nuevo/', views.GenerarTicketView.as_view(), name='generar_ticket'),

    # Triaje
    path('triage/cola/', views.ColaTriajeListView.as_view(), name='cola_triaje'),
    path('triage/evaluar/<int:pk>/', views.EvaluacionTriajeUpdateView.as_view(), name='evaluar_paciente'),

    # Médico
    path('medico/cola/', views.ColaMedicaListView.as_view(), name='cola_medica'),
    path('medico/atender/<int:pk>/', views.AtencionMedicaUpdateView.as_view(), name='atencion_medica'),
]