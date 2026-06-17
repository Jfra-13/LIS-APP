import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

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
def test_send_triaje_to_queue_no_avanza_a_consultorio():
    """El task asegura la cola en EN_ESPERA pero NO la mueve a consultorio.

    La transición EN_ESPERA -> EN_CONSULTORIO es decisión manual del médico
    ("Llamar paciente"). El worker no debe robar pacientes de la sala de espera.
    """
    user = User.objects.create_user(username="enfermera3", password="p")
    paciente = Paciente.objects.create(
        dni="32345678",
        nombres="Prueba",
        apellidos="Espera",
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

    send_triaje_to_queue.run(triaje.id)

    cola = ColaEstado.objects.get(triaje=triaje)
    assert cola.estado == ColaEstado.EstadoChoices.EN_ESPERA

    # Solo la acción manual del médico lo mueve a consultorio.
    cola.set_estado(ColaEstado.EstadoChoices.EN_CONSULTORIO)
    assert cola.estado == ColaEstado.EstadoChoices.EN_CONSULTORIO


@pytest.mark.django_db
def test_endpoint_finalizar_saca_paciente_de_la_cola(client):
    """El botón 'Finalizar' transiciona la cola a FINALIZADO y la saca de la lista."""
    group = Group.objects.get(name="Medicos")
    user = User.objects.create_user(username="medico_fin", password="p")
    user.groups.add(group)

    paciente = Paciente.objects.create(
        dni="42345678",
        nombres="Prueba",
        apellidos="Finalizar",
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
    cola.set_estado(ColaEstado.EstadoChoices.EN_CONSULTORIO)

    client.login(username="medico_fin", password="p")
    response = client.post(reverse("medico:finalizar_atencion", args=[cola.pk]))

    assert response.status_code == 302
    cola.refresh_from_db()
    assert cola.estado == ColaEstado.EstadoChoices.FINALIZADO
