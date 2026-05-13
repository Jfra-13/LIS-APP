import pytest
from unittest.mock import patch


from triage.models import Triaje
from admision.models import Paciente
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_triaje_creation_creates_cola_and_enqueues_task(client):
    User = get_user_model()
    user = User.objects.create_user(username="u", password="p")
    paciente = Paciente.objects.create(nombre="Test", dni="12345678")

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
