from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("admision/", include("admision.urls")),
    path("triage/", include("triage.urls")),
    path("consulta/", include("consulta.urls")),
    path("paciente/", include("portal_paciente.urls", namespace="portal_paciente")),
    path("auth-paciente/", include("autenticacion_paciente.urls", namespace="autenticacion_paciente")),
    path("medico/", include("medico.urls")),
]
