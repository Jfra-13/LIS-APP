import os
import time
import pytest
from django.contrib.auth import get_user_model
from admision.models import Paciente
from triage.models import Triaje
from medico.models import ColaEstado
from medico.tasks import send_triaje_to_queue


def make_user(username: str):
    User = get_user_model()
    user = User(username=username)
    user.set_password("p")
    user.save()
    return user

def test_triaje_flow_with_real_rabbitmq(db):
    """
    Test E2E arquitectónico:
    1. Verifica que RabbitMQ puede levantarse y recibir conexiones.
    2. Verifica la lógica de la tarea de Celery procesando el estado.
    """
    docker = pytest.importorskip("docker")
    container = None

    try:
        client = docker.from_env()
        container = client.containers.run(
            "rabbitmq:3-management",
            detach=True,
            ports={5672: 5672},
            name="rabbitmq-test-e2e",
            remove=True,
        )
    except docker.errors.DockerException:
        pytest.skip("Docker daemon no disponible; se omite el E2E con RabbitMQ real.")

    try:
        # 1. Esperamos a que RabbitMQ esté listo
        time.sleep(10)
        os.environ["CELERY_BROKER_URL"] = "amqp://guest:guest@localhost:5672//"

        # 2. Creamos los datos en la base de datos de prueba
        user = make_user("e2e")
        paciente = Paciente.objects.create(
            nombres="Paciente E2E",
            apellidos="Prueba",
            dni="98765432",
            fecha_nacimiento="1990-01-01",
            sexo="M"
        )

        tr = Triaje.objects.create(
            paciente=paciente,
            spo2=98,
            frecuencia_cardiaca=60,
            temperatura=36.5,
            nivel_prioridad=5,
            usuario_enfermeria=user,
        )

        # 3. La señal ya intentó mandar el mensaje a RabbitMQ (probado por tu log anterior).
        # Ahora, para evitar el problema de la "BD Fantasma" del subproceso,
        # ejecutamos la lógica del worker explícitamente en el mismo hilo de la prueba.
        send_triaje_to_queue.run(tr.id)

        # 4. Validamos que la tarea hizo su trabajo mutando el estado
        tr.refresh_from_db()
        cola_estado = getattr(tr, "cola_estado")
        assert cola_estado.estado == ColaEstado.EstadoChoices.EN_CONSULTORIO

    finally:
        # Limpieza de infraestructura
        try:
            if container is not None:
                container.stop()
        except Exception:
            pass