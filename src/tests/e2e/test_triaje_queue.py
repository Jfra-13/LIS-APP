import os
import subprocess
import time

import pytest


def test_triaje_flow_with_real_rabbitmq(db):
    """End-to-end test that starts a real RabbitMQ container and a celery worker,
    then creates a Triaje and asserts the worker processed it by observing
    ColaEstado transition to EN_CONSULTORIO.
    """
    from django.contrib.auth import get_user_model
    from admision.models import Paciente
    from triage.models import Triaje
    from medico.models import ColaEstado

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
        # Wait for RabbitMQ to be ready
        time.sleep(6)

        # Set broker env for this process
        os.environ["CELERY_BROKER_URL"] = "amqp://guest:guest@localhost:5672//"

        # Start a celery worker as a subprocess
        worker_proc = subprocess.Popen(
            ["celery", "-A", "config", "worker", "--loglevel=info"]
        )

        try:
            User = get_user_model()
            user = User.objects.create_user(username="e2e", password="p")
            paciente = Paciente.objects.create(nombre="E2E", dni="98765432")

            tr = Triaje.objects.create(
                paciente=paciente,
                spo2=98,
                frecuencia_cardiaca=60,
                temperatura=36.5,
                nivel_prioridad=5,
                usuario_enfermeria=user,
            )

            # Poll for transition by worker
            timeout = 30
            interval = 1
            elapsed = 0
            while elapsed < timeout:
                tr.refresh_from_db()
                if (
                    hasattr(tr, "cola_estado")
                    and tr.cola_estado.estado == ColaEstado.EstadoChoices.EN_CONSULTORIO
                ):
                    break
                time.sleep(interval)
                elapsed += interval

            assert hasattr(tr, "cola_estado")
            assert tr.cola_estado.estado == ColaEstado.EstadoChoices.EN_CONSULTORIO

        finally:
            worker_proc.terminate()
            worker_proc.wait(timeout=5)

    finally:
        try:
            container.stop()
        except Exception:
            pass
