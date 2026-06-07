import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from core.models import User


@pytest.mark.django_db
def test_cola_stream_requires_permission(client):
    """Sin `medico.view_colaestado` el stream responde 403 (no redirige)."""
    user = User.objects.create_user(username="sin_permiso", password="p")
    client.force_login(user)

    response = client.get(reverse("medico:cola_stream"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_cola_stream_returns_event_stream(client):
    """Con permiso, el endpoint responde como SSE sin bloquear la respuesta."""
    user = User.objects.create_user(username="con_permiso", password="p")
    user.user_permissions.add(Permission.objects.get(codename="view_colaestado"))
    client.force_login(user)

    response = client.get(reverse("medico:cola_stream"))

    # No se consume `streaming_content` (es un generador infinito): solo se
    # validan estado y cabeceras de transporte SSE.
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/event-stream")
    assert response["Cache-Control"] == "no-cache"
    assert response["X-Accel-Buffering"] == "no"
