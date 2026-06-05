from django.urls import path

from .views import PacienteTriajeHistoryView, TriajeCreateView, TriajeListView

app_name = "triage"

urlpatterns = [
    path("", TriajeListView.as_view(), name="triage_list"),
    path(
        "pacientes/<uuid:paciente_pk>/nuevo/",
        TriajeCreateView.as_view(),
        name="triage_create",
    ),
    path(
        "pacientes/<uuid:paciente_pk>/historial/",
        PacienteTriajeHistoryView.as_view(),
        name="paciente_triaje_history",
    ),
]
