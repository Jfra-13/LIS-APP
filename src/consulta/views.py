from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.db import models
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView
from datetime import datetime, time, timedelta
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views import View

from .forms import NotaMedicaForm
from .models import NotaMedica
from .services.cie_lookup import search as cie_search
from triage.models import Triaje


def consulta_health(request):
    """Endpoint técnico para verificar que la app consulta está registrada."""
    return JsonResponse({"app": "consulta", "status": "ok"})


class MedicoRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_staff or user.groups.filter(name="medico").exists()


class NotaMedicaListView(MedicoRequiredMixin, ListView):
    model = NotaMedica
    template_name = "consulta/list.html"
    context_object_name = "notas"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("paciente", "triaje", "medico")
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                models.Q(paciente__dni__icontains=q)
                | models.Q(paciente__nombres__icontains=q)
                | models.Q(paciente__apellidos__icontains=q)
                | models.Q(motivo_consulta__icontains=q)
                | models.Q(contenido__icontains=q)
            )
        return queryset.order_by("-created_at")


class NotaMedicaCreateView(MedicoRequiredMixin, CreateView):
    model = NotaMedica
    form_class = NotaMedicaForm
    template_name = "consulta/form.html"
    success_url = reverse_lazy("consulta:nota_list")

    def form_valid(self, form):
        form.instance.medico = self.request.user
        return super().form_valid(form)


class NotaMedicaDetailView(MedicoRequiredMixin, DetailView):
    model = NotaMedica
    template_name = "consulta/detail.html"
    context_object_name = "nota"


@login_required
def cie_suggest(request):
    """Endpoint JSON para sugerencias CIE-10 rule-based."""
    q = request.GET.get("q", "")
    results = cie_search(q, limit=5)
    payload = [
        {
            "code": item.get("code"),
            "short_description": item.get("short_description"),
            "description": item.get("description"),
            "group": item.get("group"),
            "severity": item.get("severity"),
            "emergency_flag": item.get("emergency_flag", False),
        }
        for item in results
    ]
    return JsonResponse({"query": q, "count": len(payload), "results": payload})


def _parse_date_param(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _make_aware(dt: datetime):
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt, timezone.get_current_timezone())


class ConsultaReportView(MedicoRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        start_param = request.GET.get("start_date")
        end_param = request.GET.get("end_date")

        start_date = _parse_date_param(start_param)
        end_date = _parse_date_param(end_param)

        if start_param and start_date is None:
            return JsonResponse({"error": "start_date inválido. Use YYYY-MM-DD."}, status=400)
        if end_param and end_date is None:
            return JsonResponse({"error": "end_date inválido. Use YYYY-MM-DD."}, status=400)

        today = timezone.localdate()
        if end_date is None:
            end_date = today
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        if start_date > end_date:
            return JsonResponse({"error": "start_date no puede ser mayor que end_date."}, status=400)

        start_dt = _make_aware(datetime.combine(start_date, time.min))
        end_dt = _make_aware(datetime.combine(end_date + timedelta(days=1), time.min))

        notas_qs = NotaMedica.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)

        cie_aggregation = (
            notas_qs.filter(cie_code__isnull=False)
            .exclude(cie_code="")
            .values("cie_code", "cie_short_description")
            .annotate(cantidad=Count("id"))
            .order_by("-cantidad", "cie_code")
        )

        triaje_qs = (
            Triaje.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
            .annotate(fecha=TruncDate("created_at"))
            .values("fecha")
            .annotate(promedio_prioridad=Avg("nivel_prioridad"))
            .order_by("fecha")
        )

        notas_recientes_qs = (
            notas_qs.select_related("paciente", "medico")
            .order_by("-created_at")[:10]
        )

        notas_recientes = []
        for nota in notas_recientes_qs:
            medico = nota.medico
            medico_nombre = ""
            if medico:
                medico_nombre = f"{medico.first_name} {medico.last_name}".strip() or medico.username
            notas_recientes.append(
                {
                    "id_nota": str(nota.pk),
                    "paciente_dni": nota.paciente.dni,
                    "fecha_creacion": nota.created_at.isoformat(),
                    "cie_code": nota.cie_code,
                    "medico": medico_nombre,
                }
            )

        payload = {
            "rango_fechas": {
                "inicio": start_date.isoformat(),
                "fin": end_date.isoformat(),
            },
            "agrupacion_cie10": [
                {
                    "cie_code": row["cie_code"],
                    "descripcion": row["cie_short_description"],
                    "cantidad": row["cantidad"],
                }
                for row in cie_aggregation
            ],
            "promedio_prioridad_triaje_diario": [
                {
                    "fecha": row["fecha"].isoformat(),
                    "promedio_prioridad": float(row["promedio_prioridad"])
                    if row["promedio_prioridad"] is not None
                    else None,
                }
                for row in triaje_qs
            ],
            "notas_recientes": notas_recientes,
        }

        return JsonResponse(payload)
