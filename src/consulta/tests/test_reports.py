from datetime import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from admision.models import Paciente
from consulta.models import NotaMedica
from core.models import User
from triage.models import Triaje


def make_medico(username: str) -> User:
    group = Group.objects.get(name="Medicos")
    user = User.objects.create_user(username=username, password="p", first_name="Juan", last_name="Perez")
    user.groups.add(group)
    return user


def make_aware_dt(value: datetime):
    if timezone.is_aware(value):
        return value
    return timezone.make_aware(value, timezone.get_current_timezone())


@pytest.mark.django_db
def test_reportes_requiere_medico(client):
    response = client.get(reverse("consulta:reportes"))
    assert response.status_code == 302

    user = User.objects.create_user(username="staff", password="p")
    client.login(username="staff", password="p")
    response = client.get(reverse("consulta:reportes"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_reportes_devuelve_agregados_y_notas_recientes(client):
    medico = make_medico("medico_reportes")
    paciente = Paciente.objects.create(
        dni="12345678",
        nombres="Ana",
        apellidos="Lopez",
        fecha_nacimiento="1990-01-01",
        sexo="F",
    )

    triaje_1 = Triaje.objects.create(
        paciente=paciente,
        spo2=98,
        frecuencia_cardiaca=72,
        temperatura=36.7,
        nivel_prioridad=2,
        usuario_enfermeria=medico,
        created_at=make_aware_dt(datetime(2026, 5, 13, 9, 0, 0)),
    )
    Triaje.objects.create(
        paciente=paciente,
        spo2=96,
        frecuencia_cardiaca=80,
        temperatura=37.1,
        nivel_prioridad=4,
        usuario_enfermeria=medico,
        created_at=make_aware_dt(datetime(2026, 5, 14, 9, 0, 0)),
    )

    NotaMedica.objects.create(
        paciente=paciente,
        triaje=triaje_1,
        medico=medico,
        motivo_consulta="Consulta",
        contenido="Nota con CIE",
        cie_code="J00",
        cie_short_description="Resfriado común",
        created_at=make_aware_dt(datetime(2026, 5, 13, 10, 0, 0)),
    )
    NotaMedica.objects.create(
        paciente=paciente,
        triaje=triaje_1,
        medico=medico,
        motivo_consulta="Consulta 2",
        contenido="Otra nota",
        cie_code="A09",
        cie_short_description="Diarrea y gastroenteritis",
        created_at=make_aware_dt(datetime(2026, 5, 14, 10, 0, 0)),
    )
    NotaMedica.objects.create(
        paciente=paciente,
        triaje=triaje_1,
        medico=medico,
        motivo_consulta="Fuera de rango",
        contenido="No debe aparecer",
        cie_code="B20",
        cie_short_description="Enfermedad por VIH",
        created_at=make_aware_dt(datetime(2026, 3, 1, 10, 0, 0)),
    )

    client.login(username="medico_reportes", password="p")
    response = client.get(
        reverse("consulta:reportes"),
        {
            "start_date": "2026-05-13",
            "end_date": "2026-05-14",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["rango_fechas"] == {"inicio": "2026-05-13", "fin": "2026-05-14"}

    cie_codes = {item["cie_code"] for item in payload["agrupacion_cie10"]}
    assert "J00" in cie_codes
    assert "A09" in cie_codes
    assert "B20" not in cie_codes

    promedio = {item["fecha"]: item["promedio_prioridad"] for item in payload["promedio_prioridad_triaje_diario"]}
    assert promedio["2026-05-13"] == 2.0
    assert promedio["2026-05-14"] == 4.0

    assert len(payload["notas_recientes"]) == 2
    nota = payload["notas_recientes"][0]
    assert nota["paciente_dni"] == "12345678"
    assert nota["medico"] == "Juan Perez"

