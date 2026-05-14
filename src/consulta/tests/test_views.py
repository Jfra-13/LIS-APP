import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from admision.models import Paciente
from core.models import User
from consulta.models import NotaMedica


def make_user(username: str) -> User:
    user = User(username=username)
    user.set_password("p")
    user.save()
    return user



@pytest.mark.django_db
def test_anon_no_puede_crear_nota(client):
    response = client.get(reverse("consulta:nota_create"))
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_medico_puede_crear_nota(client):
    group, _ = Group.objects.get_or_create(name="medico")
    user = make_user("medico1")
    user.groups.add(group)

    paciente = Paciente.objects.create(
        dni="44444444",
        nombres="Ana",
        apellidos="Perez",
        fecha_nacimiento="1990-01-01",
        sexo="F",
    )

    client.login(username="medico1", password="p")
    response = client.post(
        reverse("consulta:nota_create"),
        {
            "paciente": paciente.pk,
            "triaje": "",
            "motivo_consulta": "Dolor abdominal",
            "contenido": "Paciente con dolor abdominal de 24 horas de evolución.",
            "is_privada": "on",
        },
    )

    assert response.status_code == 302
    nota = NotaMedica.objects.get()
    assert nota.paciente == paciente
    assert nota.medico == user
    assert nota.is_privada is True


@pytest.mark.django_db
def test_medico_puede_crear_nota_con_cie_aceptado(client):
    group, _ = Group.objects.get_or_create(name="medico")
    user = make_user("medico_cie")
    user.groups.add(group)

    paciente = Paciente.objects.create(
        dni="44444445",
        nombres="Elena",
        apellidos="Torres",
        fecha_nacimiento="1991-07-07",
        sexo="F",
    )

    client.login(username="medico_cie", password="p")
    response = client.post(
        reverse("consulta:nota_create"),
        {
            "paciente": paciente.pk,
            "triaje": "",
            "motivo_consulta": "Sospecha de gastroenteritis",
            "contenido": "El médico selecciona una sugerencia CIE desde la UI.",
            "is_privada": "on",
            "cie_code": "A09",
            "cie_short_description": "Diarrea y gastroenteritis de presunto origen infeccioso",
            "cie_accepted": "true",
        },
    )

    assert response.status_code == 302

    nota = NotaMedica.objects.get()
    assert nota.paciente == paciente
    assert nota.medico == user
    assert nota.cie_code == "A09"
    assert nota.cie_short_description == "Diarrea y gastroenteritis de presunto origen infeccioso"
    assert nota.cie_accepted is True


@pytest.mark.django_db
def test_listado_y_detalle_visible_a_medico(client):
    group, _ = Group.objects.get_or_create(name="medico")
    user = make_user("medico2")
    user.groups.add(group)

    paciente = Paciente.objects.create(
        dni="55555555",
        nombres="Luis",
        apellidos="Gomez",
        fecha_nacimiento="1985-05-05",
        sexo="M",
    )
    nota = NotaMedica.objects.create(
        paciente=paciente,
        medico=user,
        motivo_consulta="Control",
        contenido="Nota de control médico.",
    )

    client.login(username="medico2", password="p")
    list_response = client.get(reverse("consulta:nota_list"))
    detail_response = client.get(reverse("consulta:nota_detail", kwargs={"pk": nota.pk}))

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert nota.contenido in detail_response.content.decode("utf-8")

