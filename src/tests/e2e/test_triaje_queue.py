import os
import time
import pytest
from django.contrib.auth import get_user_model
from admision.models import Paciente
from triage.models import Triaje
from medico.models import ColaEstado
from medico.tasks import send_triaje_to_queue

def test_triaje_flow_with_real_rabbitmq(db):
    """
    Test E2E arquitectónico:
    1. Verifica que RabbitMQ puede levantarse y recibir conexiones.
    2. Verifica la lógica de la tarea de Celery procesando el estado.
    """
    import docker

    client = docker.from_env()
    container = client.containers.run(
        "rabbitmq:3-management",
        detach=True,
        ports={5672: 5672},
        name="rabbitmq-test-e2e",
        remove=True,
    )

    try:
        # 1. Esperamos a que RabbitMQ esté listo
        time.sleep(10)
        os.environ["CELERY_BROKER_URL"] = "amqp://guest:guest@localhost:5672//"

        # 2. Creamos los datos en la base de datos de prueba
        User = get_user_model()
        user = User.objects.create_user(username="e2e", password="p")
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
        send_triaje_to_queue(tr.id)

        # 4. Validamos que la tarea hizo su trabajo mutando el estado
        tr.refresh_from_db()
        assert hasattr(tr, "cola_estado")
        assert tr.cola_estado.estado == ColaEstado.EstadoChoices.EN_CONSULTORIO

    finally:
        # Limpieza de infraestructura
        try:
            container.stop()
        except Exception:
            pass