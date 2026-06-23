from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET

from .roles import ROLE_HOME, Role, get_role, role_required


def permission_denied(request, exception=None):
    """handler403 global — renderiza el 403 en contexto (sin redirigir al home).

    El botón "Volver" usa el ``HTTP_REFERER`` (la página desde donde se hizo
    clic) sólo si pertenece al mismo host; así un referer externo no puede
    inducir un open-redirect. Sin referer válido, cae al home.
    """
    referer = request.META.get("HTTP_REFERER")
    back_url = None
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        back_url = referer

    html = render_to_string(
        "403.html",
        {"back_url": back_url, "exception": str(exception) if exception else ""},
        request=request,
    )
    return HttpResponseForbidden(html)


@require_GET
def landing(request):
    if request.user.is_authenticated:
        return redirect("home")
    return TemplateResponse(request, "core/landing.html")


@login_required
def home(request):
    """Post-login role dispatcher — redirects each role to its own dashboard."""
    role = get_role(request.user)
    target = ROLE_HOME.get(role)
    if target is None:
        # Authenticated but no recognized role — show error page.
        return render(request, "core/no_acceso.html")
    return redirect(target)


@role_required(Role.SUPERADMIN)
def dashboard_admin(request):
    from admision.models import Paciente
    from medico.models import ColaEstado
    from triage.models import Triaje
    from consulta.models import NotaMedica

    today = timezone.now().date()

    context = {
        "pacientes_hoy": Paciente.objects.filter(created_at__date=today).count(),
        "cola_activa": ColaEstado.objects.filter(
            estado__in=[
                ColaEstado.EstadoChoices.EN_ESPERA,
                ColaEstado.EstadoChoices.EN_CONSULTORIO,
            ]
        ).count(),
        "triajes_hoy": Triaje.objects.filter(created_at__date=today).count(),
        "notas_hoy": NotaMedica.objects.filter(created_at__date=today).count(),
    }
    return TemplateResponse(request, "core/dashboard/admin.html", context)


@role_required(Role.MEDICO)
def dashboard_medico(request):
    from medico.models import ColaEstado
    from consulta.models import NotaMedica

    today = timezone.now().date()

    context = {
        "en_espera": ColaEstado.objects.filter(
            estado=ColaEstado.EstadoChoices.EN_ESPERA
        ).count(),
        "en_consultorio": ColaEstado.objects.filter(
            estado=ColaEstado.EstadoChoices.EN_CONSULTORIO
        ).count(),
        "notas_hoy": NotaMedica.objects.filter(
            medico=request.user, created_at__date=today
        ).count(),
    }
    return TemplateResponse(request, "core/dashboard/medico.html", context)


@role_required(Role.ENFERMERO)
def dashboard_enfermero(request):
    from triage.models import Triaje
    from medico.models import ColaEstado

    today = timezone.now().date()

    # Patients in the queue that haven't been triaged yet can't be directly
    # queried here (no intermediate "awaiting triage" model). We use the
    # count of today's triages as the key metric for the nurse.
    context = {
        "triajes_hoy": Triaje.objects.filter(created_at__date=today).count(),
        "en_espera": ColaEstado.objects.filter(
            estado=ColaEstado.EstadoChoices.EN_ESPERA
        ).count(),
        "red_flags_hoy": Triaje.objects.filter(
            created_at__date=today
        ).exclude(red_flag=Triaje.RedFlagChoices.NONE).count(),
    }
    return TemplateResponse(request, "core/dashboard/enfermero.html", context)


@role_required(Role.ADMISION)
def dashboard_admision(request):
    from admision.models import Paciente
    from medico.models import ColaEstado

    today = timezone.now().date()

    context = {
        "pacientes_hoy": Paciente.objects.filter(created_at__date=today).count(),
        "total_pacientes": Paciente.objects.filter(estado="activo").count(),
        "en_cola": ColaEstado.objects.filter(
            estado__in=[
                ColaEstado.EstadoChoices.EN_ESPERA,
                ColaEstado.EstadoChoices.EN_CONSULTORIO,
            ]
        ).count(),
    }
    return TemplateResponse(request, "core/dashboard/admision.html", context)
