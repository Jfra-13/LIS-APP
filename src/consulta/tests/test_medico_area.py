"""Tests para el área del médico (P3): Mis pacientes y Mi día."""
import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from admision.models import Paciente
from core.models import User
from consulta.models import NotaMedica


def _medico(username: str) -> User:
    user = User(username=username)
    user.set_password("p")
    user.save()
    user.groups.add(Group.objects.get(name="Medicos"))
    return user


def _paciente(dni: str, nombres: str = "Ana", apellidos: str = "Perez") -> Paciente:
    return Paciente.objects.create(
        dni=dni,
        nombres=nombres,
        apellidos=apellidos,
        fecha_nacimiento="1990-01-01",
        sexo="F",
    )


@pytest.mark.django_db
def test_mis_pacientes_ordena_por_atencion_reciente(client):
    medico = _medico("medico_mp")
    p_viejo = _paciente("10000001", apellidos="Antiguo")
    p_nuevo = _paciente("10000002", apellidos="Reciente")

    # Dos notas del mismo médico; la del paciente "nuevo" se crea después.
    NotaMedica.objects.create(paciente=p_viejo, medico=medico, contenido="x")
    NotaMedica.objects.create(paciente=p_nuevo, medico=medico, contenido="y")

    client.login(username="medico_mp", password="p")
    response = client.get(reverse("consulta:mis_pacientes"))

    assert response.status_code == 200
    pacientes = list(response.context["pacientes"])
    assert pacientes[0] == p_nuevo  # atención más reciente primero
    assert p_viejo in pacientes


@pytest.mark.django_db
def test_mis_pacientes_solo_del_medico_autenticado(client):
    medico = _medico("medico_a")
    otro = _medico("medico_b")
    mio = _paciente("20000001", apellidos="Mio")
    ajeno = _paciente("20000002", apellidos="Ajeno")

    NotaMedica.objects.create(paciente=mio, medico=medico, contenido="x")
    NotaMedica.objects.create(paciente=ajeno, medico=otro, contenido="y")

    client.login(username="medico_a", password="p")
    response = client.get(reverse("consulta:mis_pacientes"))

    pacientes = list(response.context["pacientes"])
    assert mio in pacientes
    assert ajeno not in pacientes


@pytest.mark.django_db
def test_mis_pacientes_cuenta_solo_notas_del_medico(client):
    medico = _medico("medico_c")
    otro = _medico("medico_d")
    paciente = _paciente("30000001")

    NotaMedica.objects.create(paciente=paciente, medico=medico, contenido="x")
    NotaMedica.objects.create(paciente=paciente, medico=medico, contenido="y")
    NotaMedica.objects.create(paciente=paciente, medico=otro, contenido="z")

    client.login(username="medico_c", password="p")
    response = client.get(reverse("consulta:mis_pacientes"))

    paciente_row = list(response.context["pacientes"])[0]
    assert paciente_row.num_notas == 2  # no cuenta la nota del otro médico


@pytest.mark.django_db
def test_mi_dia_resumen(client):
    medico = _medico("medico_dia")
    paciente = _paciente("40000001")
    NotaMedica.objects.create(paciente=paciente, medico=medico, contenido="x")

    client.login(username="medico_dia", password="p")
    response = client.get(reverse("consulta:mi_dia"))

    assert response.status_code == 200
    assert response.context["notas_hoy"] == 1
    assert response.context["pacientes_hoy"] == 1


@pytest.mark.django_db
def test_mis_pacientes_requiere_permiso(client):
    user = User(username="sin_permiso")
    user.set_password("p")
    user.save()
    client.login(username="sin_permiso", password="p")

    response = client.get(reverse("consulta:mis_pacientes"))
    assert response.status_code == 403
