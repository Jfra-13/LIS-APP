"""
Template context processors for the LIS app shell.
"""
from .navigation import ROLE_LABELS, nav_items_for
from .roles import Role, get_role


def navigation(request):
    """
    Inject navigation context into every template.

    Returns:
        current_role       -- Role enum value or None
        current_role_label -- Spanish label string or empty string
        nav_items          -- list of nav item dicts for the sidebar
        is_patient_shell   -- True when the page should use the lighter patient shell
                              (no staff sidebar, full-width content)
    """
    # Guard: request may not have a user attribute in some edge cases.
    user = getattr(request, "user", None)
    if user is None:
        return {
            "current_role": None,
            "current_role_label": "",
            "nav_items": [],
            "is_patient_shell": True,
        }

    role = get_role(user)
    label = ROLE_LABELS.get(role, "")
    items = nav_items_for(role, request)
    is_patient_shell = role == Role.PACIENTE or role is None

    return {
        "current_role": role,
        "current_role_label": label,
        "nav_items": items,
        "is_patient_shell": is_patient_shell,
    }
