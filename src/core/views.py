from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET

from .roles import ROLE_HOME, Role, get_role, role_required


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
    return TemplateResponse(request, "core/dashboard/admin.html")


@role_required(Role.MEDICO)
def dashboard_medico(request):
    return TemplateResponse(request, "core/dashboard/medico.html")


@role_required(Role.ENFERMERO)
def dashboard_enfermero(request):
    return TemplateResponse(request, "core/dashboard/enfermero.html")


@role_required(Role.ADMISION)
def dashboard_admision(request):
    return TemplateResponse(request, "core/dashboard/admision.html")
