from django.urls import path

from .views import (
    NotaMedicaCreateView,
    NotaMedicaDetailView,
    NotaMedicaListView,
    consulta_health,
    cie_suggest,
    ConsultaReportView,
)

app_name = "consulta"

urlpatterns = [
    path("", NotaMedicaListView.as_view(), name="nota_list"),
    path("health/", consulta_health, name="health"),
    path("nueva/", NotaMedicaCreateView.as_view(), name="nota_create"),
    path("<uuid:pk>/", NotaMedicaDetailView.as_view(), name="nota_detail"),
    path("api/cie-suggest/", cie_suggest, name="cie_suggest"),
    path("api/reportes/", ConsultaReportView.as_view(), name="reportes"),
]
