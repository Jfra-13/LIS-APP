import contextlib

import pytest

from admision.models import Paciente
from core.models import User
from medico.models import ColaEstado
from medico.tasks import send_triaje_to_queue
from triage.models import Triaje


@pytest.mark.django_db
def test_can_transition_permits_expected_paths():
    user = User.objects.create_user(username="enfermera", password="p")
    paciente = Paciente.objects.create(
        dni="12345678",
        nombres="Prueba",
        apellidos="Transicion",
        fecha_nacimiento="1990-01-01",
        sexo="M",
    )
    triaje = Triaje.objects.create(
        paciente=paciente,
        spo2=98,
        frecuencia_cardiaca=72,
        temperatura=36.7,
        nivel_prioridad=4,
        usuario_enfermeria=user,
    )

    cola = ColaEstado.objects.get(triaje=triaje)
    assert cola.can_transition(ColaEstado.EstadoChoices.EN_CONSULTORIO)
    assert cola.can_transition(ColaEstado.EstadoChoices.FINALIZADO)

    cola.set_estado(ColaEstado.EstadoChoices.EN_CONSULTORIO)
    assert cola.can_transition(ColaEstado.EstadoChoices.FINALIZADO)


@pytest.mark.django_db
def test_set_estado_rejects_invalid_transition():
    user = User.objects.create_user(username="enfermera2", password="p")
    paciente = Paciente.objects.create(
        dni="22345678",
        nombres="Prueba",
        apellidos="Invalida",
        fecha_nacimiento="1990-01-01",
        sexo="M",
    )
    triaje = Triaje.objects.create(
        paciente=paciente,
        spo2=98,
        frecuencia_cardiaca=72,
        temperatura=36.7,
        nivel_prioridad=4,
        usuario_enfermeria=user,
    )

    cola = ColaEstado.objects.get(triaje=triaje)
    cola.set_estado(ColaEstado.EstadoChoices.FINALIZADO)

    with pytest.raises(ValueError):
        cola.set_estado(ColaEstado.EstadoChoices.EN_CONSULTORIO)


@pytest.mark.django_db
def test_send_triaje_to_queue_uses_row_lock_inside_atomic(monkeypatch):
    user = User.objects.create_user(username="enfermera3", password="p")
    paciente = Paciente.objects.create(
        dni="32345678",
        nombres="Prueba",
        apellidos="Lock",
        fecha_nacimiento="1990-01-01",
        sexo="M",
    )
    triaje = Triaje.objects.create(
        paciente=paciente,
        spo2=98,
        frecuencia_cardiaca=72,
        temperatura=36.7,
        nivel_prioridad=4,
        usuario_enfermeria=user,
    )

    in_atomic = {"value": False}

    @contextlib.contextmanager
    def fake_atomic():
        in_atomic["value"] = True
        try:
            yield
        finally:
            in_atomic["value"] = False

    original_manager = ColaEstado.objects

    def fake_select_for_update(*args, **kwargs):
        assert in_atomic["value"] is True
        return original_manager.all()

    monkeypatch.setattr("medico.tasks.transaction.atomic", fake_atomic)
    monkeypatch.setattr(ColaEstado.objects, "select_for_update", fake_select_for_update)

    send_triaje_to_queue.run(triaje.id)

    cola = ColaEstado.objects.get(triaje=triaje)
    assert cola.estado == ColaEstado.EstadoChoices.EN_CONSULTORIO

