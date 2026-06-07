import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView
from datetime import datetime, time, timedelta
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views import View
from django.shortcuts import get_object_or_404

from .forms import NotaMedicaForm
from .models import NotaMedica
from .services.cie_lookup import search as cie_search
from .services.med_lookup import search as med_search
from triage.models import Triaje


logger = logging.getLogger(__name__)


def consulta_health(request):
    """Endpoint técnico para verificar que la app consulta está registrada."""
    return JsonResponse({"app": "consulta", "status": "ok"})


class ConsultaPermissionMixin(PermissionRequiredMixin):
    """
    Verifica los permisos para el módulo de consulta.

    Usa el comportamiento estándar de Django:
    - Usuario anónimo: redirección a login (302).
    - Usuario autenticado sin permiso: 403 Forbidden.
    """

    pass


class NotaMedicaListView(ConsultaPermissionMixin, ListView):
    model = NotaMedica
    permission_required = "consulta.view_notamedica"
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


class NotaMedicaCreateView(ConsultaPermissionMixin, CreateView):
    model = NotaMedica
    form_class = NotaMedicaForm
    permission_required = "consulta.add_notamedica"
    template_name = "consulta/form.html"
    success_url = reverse_lazy("consulta:nota_list")

    def get_initial(self):
        initial = super().get_initial()
        paciente_id = self.request.GET.get("paciente")
        triaje_id = self.request.GET.get("triaje")
        if paciente_id:
            initial["paciente"] = paciente_id
        if triaje_id:
            initial["triaje"] = triaje_id
        return initial

    def form_valid(self, form):
        form.instance.medico = self.request.user
        response = super().form_valid(form)
        # Disparar el procesamiento NLP en segundo plano (RF-06). Es un efecto
        # secundario fire-and-forget: si falla, la nota ya quedó guardada y la
        # pantalla del médico nunca se bloquea esperando la IA.
        try:
            from .tasks import process_clinical_note

            process_clinical_note.delay(self.object.id)
        except Exception:
            logger.exception(
                "No se pudo encolar process_clinical_note",
                extra={"nota_id": str(self.object.id)},
            )
        return response


class NotaMedicaDetailView(ConsultaPermissionMixin, DetailView):
    model = NotaMedica
    permission_required = "consulta.view_notamedica"
    template_name = "consulta/detail.html"
    context_object_name = "nota"


@login_required
def cie_suggest(request):
    """Endpoint JSON para sugerencias CIE-10. Soporta HTMX."""
    q = request.GET.get("q", "")
    results = cie_search(q, limit=5)
    
    if request.headers.get('HX-Request'):
        html = ""
        for item in results:
            html += f"""
            <button type="button" class="list-group-item list-group-item-action cie-item border-0 small" 
                    data-code="{item.get('code')}" 
                    data-description="{item.get('short_description')}">
                <div class="d-flex justify-content-between">
                    <span class="fw-bold">{item.get('code')}</span>
                    <span class="badge bg-light text-muted small">{item.get('group')}</span>
                </div>
                <div class="text-truncate">{item.get('short_description')}</div>
            </button>
            """
        if not html:
            html = '<div class="p-3 text-muted small">Sin sugerencias.</div>'
        return HttpResponse(html)

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


@login_required
def med_suggest(request):
    """Endpoint JSON para búsqueda de medicamentos. Soporta HTMX."""
    q = request.GET.get("q", "")
    results = med_search(q, limit=10)

    if request.headers.get('HX-Request'):
        html = ""
        for item in results:
            html += f"""
            <button type="button" class="list-group-item list-group-item-action med-item border-0 small" 
                    data-id="{item.get('id')}" 
                    data-nombre="{item.get('nombre')}">
                <div class="fw-bold">{item.get('nombre')}</div>
                <div class="text-muted small">{item.get('presentacion')} - {item.get('concentracion')}</div>
            </button>
            """
        if not html:
            html = '<div class="p-3 text-muted small">No se encontraron medicamentos.</div>'
        return HttpResponse(html)

    payload = [
        {
            "id": item.get("id"),
            "nombre": item.get("nombre"),
            "presentacion": item.get("presentacion"),
            "concentracion": item.get("concentracion"),
            "label": f"{item.get('nombre')} ({item.get('presentacion')} - {item.get('concentracion')})"
        }
        for item in results
    ]
    return JsonResponse({"query": q, "count": len(payload), "results": payload})


def _ai_status(estado: str) -> str:
    """Mapea el estado interno de la nota al contrato público del endpoint."""
    return {
        NotaMedica.EstadoIA.LISTO: "ready",
        NotaMedica.EstadoIA.ERROR: "error",
    }.get(estado, "processing")


def _render_ai_panel(nota) -> str:
    """Fragmento HTML del panel de IA para el polling HTMX (detail.html)."""
    if nota.estado_ia == NotaMedica.EstadoIA.LISTO:
        suggestions = nota.cie_suggestions or []
        if not suggestions:
            body = '<div class="text-muted small">Sin sugerencias para esta nota.</div>'
        else:
            items = ""
            for item in suggestions:
                items += f"""
                <div class="list-group-item small">
                    <span class="fw-bold">{item.get('code')}</span>
                    <span class="text-muted">{item.get('short_description')}</span>
                </div>
                """
            body = f'<div class="list-group list-group-flush">{items}</div>'
        return f'<div id="ia-panel"><h6 class="fw-bold">Sugerencias IA (CIE-10)</h6>{body}</div>'

    if nota.estado_ia == NotaMedica.EstadoIA.ERROR:
        return (
            '<div id="ia-panel"><span class="text-danger small">'
            "No se pudo procesar la nota con la IA.</span></div>"
        )

    # PENDIENTE / PROCESANDO: el div mantiene el polling cada 2s.
    return (
        '<div id="ia-panel" hx-get="" hx-trigger="every 2s" hx-swap="outerHTML" '
        'hx-include="this">'
        '<span class="text-muted small">Procesando IA…</span></div>'
    )


@login_required
def get_ai_suggestions(request, pk):
    """Estado y sugerencias de IA de una nota, leídos de la BD (sin Redis)."""
    nota = get_object_or_404(NotaMedica, pk=pk)

    if request.headers.get("HX-Request"):
        # El polling HTMX necesita la URL en el div que se reinyecta.
        url = reverse_lazy("consulta:ai_suggestions", kwargs={"pk": nota.pk})
        html = _render_ai_panel(nota).replace('hx-get=""', f'hx-get="{url}"')
        return HttpResponse(html)

    status = _ai_status(nota.estado_ia)
    payload = {
        "status": status,
        "estado": nota.estado_ia,
        "suggestions": nota.cie_suggestions or [],
    }
    http_status = 200 if status in ("ready", "error") else 202
    return JsonResponse(payload, status=http_status)


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


class ConsultaReportView(ConsultaPermissionMixin, View):
    permission_required = "consulta.view_notamedica"

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
