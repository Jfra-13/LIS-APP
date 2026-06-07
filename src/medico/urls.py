from django.urls import path
from .views import ColaAtencionListView, LlamarPacienteView, cola_stream

app_name = "medico"

urlpatterns = [
    path("cola/", ColaAtencionListView.as_view(), name="cola_atencion"),
    path("cola/stream/", cola_stream, name="cola_stream"),
    path("cola/<int:pk>/llamar/", LlamarPacienteView.as_view(), name="llamar_paciente"),
]
