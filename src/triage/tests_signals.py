import pytest
from unittest.mock import patch


from triage.models import Triaje
from admision.models import Paciente
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_triaje_creation_creates_cola_and_enqueues_task(client):
    User = get_user_model()
    user = User.objects.create_user(username="u", password="p")
    # Crear paciente con los campos requeridos del modelo
    paciente = Paciente.objects.create(
        dni="12345678",
        nombres="Test",
        apellidos="Paciente",
        fecha_nacimiento="1990-01-01",
        sexo="M",
    )

    # Parchear la función del task en el módulo medico (la señal la importa localmente)
    with patch("medico.tasks.send_triaje_to_queue.delay") as mock_delay:
        tr = Triaje.objects.create(
            paciente=paciente,
            spo2=98,
            frecuencia_cardiaca=60,
            temperatura=36.5,
            nivel_prioridad=5,
            usuario_enfermeria=user,
        )

        # Ensure task was enqueued
        mock_delay.assert_called_once_with(tr.id)

        # Ensure ColaEstado exists
        assert hasattr(tr, "cola_estado")
        assert tr.cola_estado.estado == tr.cola_estado.EstadoChoices.EN_ESPERA
