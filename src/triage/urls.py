from django.urls import path

from .views import TriajeCreateView

app_name = 'triage'

urlpatterns = [
    path('pacientes/<uuid:paciente_pk>/nuevo/', TriajeCreateView.as_view(), name='triage_create'),
]
