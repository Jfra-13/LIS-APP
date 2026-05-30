from django.urls import path

from .views import TriajeCreateView, TriajeListView

app_name = "triage"

urlpatterns = [
    path("", TriajeListView.as_view(), name="triage_list"),
    path(
        "pacientes/<uuid:paciente_pk>/nuevo/",
        TriajeCreateView.as_view(),
        name="triage_create",
    ),
]
