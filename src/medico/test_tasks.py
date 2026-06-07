import pytest

from admision.models import Paciente
from core.models import User
from medico.models import ColaEstado
from medico.tasks import send_triaje_to_queue
from triage.models import Triaje


@pytest.mark.django_db
def test_send_triaje_to_queue_acepta_uuid_y_mantiene_en_espera():
    user = User.objects.create_user(username="enfermera", password="p")
    paciente = Paciente.objects.create(
        dni="99999999",
        nombres="Prueba",
        apellidos="Task",
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
    assert cola.estado == ColaEstado.EstadoChoices.EN_ESPERA

    # El task asegura la cola pero NO avanza a consultorio: eso lo decide el médico.
    send_triaje_to_queue.run(triaje.id)

    cola.refresh_from_db()
    assert cola.estado == ColaEstado.EstadoChoices.EN_ESPERA

    # Idempotencia: re-ejecutar (acepta str) no rompe ni cambia el estado.
    send_triaje_to_queue.run(str(triaje.id))
    cola.refresh_from_db()
    assert cola.estado == ColaEstado.EstadoChoices.EN_ESPERA
