"""
Single source of truth for role resolution in app-LIS.

Groups (no accents): Medicos, Enfermeros, Admision, Pacientes.
Superadmin is NOT a group — it is user.is_superuser.
"""
import enum
import functools

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class Role(str, enum.Enum):
    SUPERADMIN = "SUPERADMIN"
    MEDICO = "MEDICO"
    ENFERMERO = "ENFERMERO"
    ADMISION = "ADMISION"
    PACIENTE = "PACIENTE"


# Map from group name to Role — in resolution priority order.
_GROUP_TO_ROLE = [
    ("Medicos", Role.MEDICO),
    ("Enfermeros", Role.ENFERMERO),
    ("Admision", Role.ADMISION),
    ("Pacientes", Role.PACIENTE),
]

# Role → named URL for that role's landing page.
ROLE_HOME = {
    Role.SUPERADMIN: "dashboard_admin",
    Role.MEDICO: "dashboard_medico",
    Role.ENFERMERO: "dashboard_enfermero",
    Role.ADMISION: "dashboard_admision",
    Role.PACIENTE: "portal_paciente:dashboard",
}


def get_role(user) -> "Role | None":
    """
    Resolve the role of *user*.

    Returns None for anonymous users or authenticated users with no recognized
    role assignment.  Uses a single DB query (values_list) to avoid N+1.
    Priority: SUPERADMIN > MEDICO > ENFERMERO > ADMISION > PACIENTE.
    """
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return Role.SUPERADMIN

    group_names = set(user.groups.values_list("name", flat=True))
    for group_name, role in _GROUP_TO_ROLE:
        if group_name in group_names:
            return role

    return None


def role_required(*allowed_roles):
    """
    View decorator that enforces role-based access control.

    - Unauthenticated users → redirect to 'login'.
    - Authenticated users whose role is not in *allowed_roles* → 403.
    - Authenticated users with the correct role → view is called normally.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            role = get_role(request.user)
            if role not in allowed_roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
