import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from admision.models import Paciente
from consulta.models import NotaMedica
from consulta.tasks import process_clinical_note
from consulta.views import _render_ai_panel
from core.models import User


class _StubNota:
    """Stub liviano para _render_ai_panel (no toca la BD)."""

    def __init__(self, **kwargs):
        self.cie_accepted = kwargs.get("cie_accepted", False)
        self.cie_code = kwargs.get("cie_code")
        self.cie_short_description = kwargs.get("cie_short_description")
        self.estado_ia = kwargs.get("estado_ia", NotaMedica.EstadoIA.LISTO)
        self.cie_suggestions = kwargs.get("cie_suggestions", [])


def test_ai_panel_muestra_cie_establecido_no_sugerencias():
    """Con CIE aceptado, el panel muestra solo el establecido (T4.a)."""
    nota = _StubNota(
        cie_accepted=True,
        cie_code="J00",
        cie_short_description="Resfriado común",
        cie_suggestions=[{"code": "R51", "short_description": "Cefalea"}],
    )
    html = _render_ai_panel(nota)
    assert "CIE-10 establecido" in html
    assert "J00" in html
    assert "R51" not in html  # las sugerencias no se muestran


def _paciente(dni: str = "60000001") -> Paciente:
    return Paciente.objects.create(
        dni=dni,
        nombres="Test",
        apellidos="IA",
        fecha_nacimiento="1990-01-01",
        sexo="M",
    )


def _medico(username: str = "medico_ia") -> User:
    group = Group.objects.get(name="Medicos")
    user = User(username=username)
    user.set_password("p")
    user.save()
    user.groups.add(group)
    return user


@pytest.fixture
def celery_eager(settings):
    """Ejecuta los tasks de forma síncrona (CELERY_TASK_ALWAYS_EAGER).

    La conf de Celery se carga vía ``config_from_object('django.conf:settings')``,
    así que hay que mutar el setting y forzar la recarga; asignar directo a
    ``app.conf`` no surte efecto con ese loader.
    """
    from config.celery import app

    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    app.config_from_object("django.conf:settings", namespace="CELERY", force=True)
    yield
    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.CELERY_TASK_EAGER_PROPAGATES = False
    app.config_from_object("django.conf:settings", namespace="CELERY", force=True)


@pytest.mark.django_db
def test_process_clinical_note_marca_listo_y_persiste_sugerencias():
    nota = NotaMedica.objects.create(
        paciente=_paciente(),
        motivo_consulta="Dolor de cabeza",
        contenido="Paciente refiere cefalea intensa y fiebre.",
    )
    assert nota.estado_ia == NotaMedica.EstadoIA.PENDIENTE

    process_clinical_note.apply(args=[str(nota.pk)])

    nota.refresh_from_db()
    assert nota.estado_ia == NotaMedica.EstadoIA.LISTO
    assert isinstance(nota.cie_suggestions, list)
    # La IA SUGIERE; el diagnóstico confirmado del médico no debe tocarse.
    assert nota.cie_code in (None, "")
    assert nota.cie_accepted is False


@pytest.mark.django_db
def test_process_clinical_note_no_pisa_diagnostico_del_medico():
    nota = NotaMedica.objects.create(
        paciente=_paciente(),
        motivo_consulta="Fiebre",
        contenido="Cuadro febril.",
        cie_code="A09",
        cie_short_description="Diarrea y gastroenteritis",
        cie_accepted=True,
    )

    process_clinical_note.apply(args=[str(nota.pk)])

    nota.refresh_from_db()
    assert nota.cie_code == "A09"
    assert nota.cie_accepted is True
    assert nota.estado_ia == NotaMedica.EstadoIA.LISTO


@pytest.mark.django_db
def test_process_clinical_note_degrada_sin_spacy(monkeypatch):
    """Si spaCy no está disponible, el motor cae a texto crudo sin romper."""
    from consulta.services import nlp_service

    def boom(*args, **kwargs):
        raise OSError("modelo es_core_news_sm no instalado")

    monkeypatch.setattr(nlp_service, "extract_entities", boom)

    nota = NotaMedica.objects.create(
        paciente=_paciente(),
        contenido="Dolor abdominal agudo.",
    )

    process_clinical_note.apply(args=[str(nota.pk)])

    nota.refresh_from_db()
    assert nota.estado_ia == NotaMedica.EstadoIA.LISTO


@pytest.mark.django_db
def test_process_clinical_note_marca_error_si_motor_falla(monkeypatch):
    from consulta.services import suggestion_engine

    def boom(*args, **kwargs):
        raise RuntimeError("fallo del catálogo")

    monkeypatch.setattr(suggestion_engine, "suggest_cie", boom)

    nota = NotaMedica.objects.create(
        paciente=_paciente(),
        contenido="Texto clínico.",
    )

    process_clinical_note.apply(args=[str(nota.pk)])

    nota.refresh_from_db()
    assert nota.estado_ia == NotaMedica.EstadoIA.ERROR


@pytest.mark.django_db
def test_flujo_completo_crear_nota_dispara_ia(client, celery_eager):
    user = _medico("medico_flujo")
    paciente = _paciente()
    client.login(username="medico_flujo", password="p")

    response = client.post(
        reverse("consulta:nota_create"),
        {
            "paciente": paciente.pk,
            "triaje": "",
            "motivo_consulta": "Dolor de cabeza",
            "contenido": "Cefalea y fiebre de 24 horas.",
            "is_privada": "on",
        },
    )

    assert response.status_code == 302
    nota = NotaMedica.objects.get()
    assert nota.medico == user
    assert nota.estado_ia == NotaMedica.EstadoIA.LISTO


@pytest.mark.django_db
def test_ai_suggestions_endpoint_listo(client):
    _medico("medico_endpoint")
    nota = NotaMedica.objects.create(
        paciente=_paciente(),
        contenido="x",
        estado_ia=NotaMedica.EstadoIA.LISTO,
        cie_suggestions=[{"code": "R51", "short_description": "Cefalea"}],
    )
    client.login(username="medico_endpoint", password="p")

    response = client.get(reverse("consulta:ai_suggestions", kwargs={"pk": nota.pk}))

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["suggestions"][0]["code"] == "R51"


@pytest.mark.django_db
def test_ai_suggestions_endpoint_procesando(client):
    _medico("medico_proc")
    nota = NotaMedica.objects.create(paciente=_paciente(), contenido="x")
    client.login(username="medico_proc", password="p")

    response = client.get(reverse("consulta:ai_suggestions", kwargs={"pk": nota.pk}))

    assert response.status_code == 202
    assert response.json()["status"] == "processing"
