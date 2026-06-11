"""
Role-scoped navigation builder for the LIS app shell.

nav_items_for(role, request) returns the sidebar navigation list for a given
role. Each item is a dict with keys: label, url, icon, active.
"""
from django.urls import reverse

from .roles import Role

# Spanish labels for each role (used in the topbar chip).
ROLE_LABELS = {
    Role.SUPERADMIN: "Administrador",
    Role.MEDICO: "Médico",
    Role.ENFERMERO: "Enfermería",
    Role.ADMISION: "Admisión",
    Role.PACIENTE: "Paciente",
}


def _item(label: str, url: str, icon: str, request) -> dict:
    """Build a nav item dict, computing active state from the request path."""
    # For the root dashboard URLs we want an exact match to avoid false positives.
    # For all other URLs a startswith is fine.
    active = request.path == url if url.startswith("/dashboard/") or url == "/admin/" else request.path.startswith(url)
    return {"label": label, "url": url, "icon": icon, "active": active}


def nav_items_for(role, request) -> list:
    """
    Return the navigation items for *role*.

    Returns an empty list for None (anonymous / no-role).
    """
    if role is None:
        return []

    if role == Role.SUPERADMIN:
        return [
            _item("Dashboard", reverse("dashboard_admin"), "bi-speedometer2", request),
            _item("Admin Django", "/admin/", "bi-gear", request),
        ]

    if role == Role.MEDICO:
        return [
            _item("Dashboard", reverse("dashboard_medico"), "bi-speedometer2", request),
            _item("Cola de atención", reverse("medico:cola_atencion"), "bi-megaphone", request),
            _item("Notas clínicas", reverse("consulta:nota_list"), "bi-journal-medical", request),
        ]

    if role == Role.ENFERMERO:
        return [
            _item("Dashboard", reverse("dashboard_enfermero"), "bi-speedometer2", request),
            _item("Triaje", reverse("triage:triage_list"), "bi-clipboard-pulse", request),
        ]

    if role == Role.ADMISION:
        return [
            _item("Dashboard", reverse("dashboard_admision"), "bi-speedometer2", request),
            _item("Pacientes", reverse("admision:paciente_list"), "bi-people", request),
        ]

    if role == Role.PACIENTE:
        return [
            _item("Mis recetas", reverse("portal_paciente:dashboard"), "bi-file-medical", request),
        ]

    return []
