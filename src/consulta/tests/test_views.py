import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from admision.models import Paciente
from core.models import User
from consulta.models import Medicamento, NotaMedica
from medico.models import ColaEstado
from triage.models import Triaje


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
    group = Group.objects.get(name="Medicos")
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
    group = Group.objects.get(name="Medicos")
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
def test_crear_nota_finaliza_la_cola_del_triaje(client):
    """Guardar la nota cierra la consulta: la cola pasa a FINALIZADO."""
    group = Group.objects.get(name="Medicos")
    user = make_user("medico_cola")
    user.groups.add(group)

    paciente = Paciente.objects.create(
        dni="66666666",
        nombres="Mario",
        apellidos="Diaz",
        fecha_nacimiento="1980-03-03",
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

    client.login(username="medico_cola", password="p")
    response = client.post(
        reverse("consulta:nota_create"),
        {
            "paciente": paciente.pk,
            "triaje": triaje.pk,
            "motivo_consulta": "Control",
            "contenido": "Consulta atendida, se cierra la atención.",
        },
    )

    assert response.status_code == 302
    cola.refresh_from_db()
    assert cola.estado == ColaEstado.EstadoChoices.FINALIZADO


@pytest.mark.django_db
def test_crear_nota_con_prescripcion_la_persiste(client):
    """Una fila de receta válida se guarda como Prescripcion ligada a la nota."""
    group = Group.objects.get(name="Medicos")
    user = make_user("medico_rx")
    user.groups.add(group)

    paciente = Paciente.objects.create(
        dni="88888888",
        nombres="Pedro",
        apellidos="Ruiz",
        fecha_nacimiento="1988-08-08",
        sexo="M",
    )
    medicamento = Medicamento.objects.create(
        nombre="Paracetamol", presentacion="Tabletas", concentracion="500mg"
    )

    client.login(username="medico_rx", password="p")
    response = client.post(
        reverse("consulta:nota_create"),
        {
            "paciente": paciente.pk,
            "triaje": "",
            "motivo_consulta": "Fiebre",
            "contenido": "Se indica antipirético.",
            "prescripciones-TOTAL_FORMS": "1",
            "prescripciones-INITIAL_FORMS": "0",
            "prescripciones-MIN_NUM_FORMS": "0",
            "prescripciones-MAX_NUM_FORMS": "1000",
            "prescripciones-0-medicamento": str(medicamento.pk),
            "prescripciones-0-dosis": "1 tableta",
            "prescripciones-0-frecuencia": "cada 8 h",
            "prescripciones-0-duracion": "3 días",
            "prescripciones-0-instrucciones_adicionales": "",
            "prescripciones-0-id": "",
            "prescripciones-0-DELETE": "",
        },
    )

    assert response.status_code == 302
    nota = NotaMedica.objects.get(paciente=paciente)
    assert nota.prescripciones.count() == 1
    assert nota.prescripciones.first().medicamento == medicamento


@pytest.mark.django_db
def test_crear_nota_sin_triaje_no_rompe(client):
    """Una nota sin triaje no tiene cola que finalizar y no debe fallar."""
    group = Group.objects.get(name="Medicos")
    user = make_user("medico_sin_cola")
    user.groups.add(group)

    paciente = Paciente.objects.create(
        dni="77777777",
        nombres="Sara",
        apellidos="Luna",
        fecha_nacimiento="1995-09-09",
        sexo="F",
    )

    client.login(username="medico_sin_cola", password="p")
    response = client.post(
        reverse("consulta:nota_create"),
        {
            "paciente": paciente.pk,
            "triaje": "",
            "motivo_consulta": "Consulta directa",
            "contenido": "Nota sin paso por la cola de triaje.",
        },
    )

    assert response.status_code == 302
    assert NotaMedica.objects.filter(paciente=paciente).exists()


@pytest.mark.django_db
def test_med_suggest_by_cie_devuelve_meds_del_mapa(client):
    """El endpoint sugiere los medicamentos mapeados al CIE que existen en DB."""
    make_user("medico_sug")
    med = Medicamento.objects.create(
        nombre="Paracetamol", presentacion="Tabletas", concentracion="500mg"
    )

    client.login(username="medico_sug", password="p")
    response = client.get(reverse("consulta:med_suggest_cie"), {"cie": "R51"})

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "med-item" in body
    assert str(med.pk) in body
    assert "Paracetamol" in body


@pytest.mark.django_db
def test_historia_clinica_combina_notas_y_triajes(client):
    """La historia clínica lista consultas (médico) y triajes (enfermero) juntos."""
    group = Group.objects.get(name="Medicos")
    user = make_user("medico_hist")
    user.groups.add(group)

    paciente = Paciente.objects.create(
        dni="99999999",
        nombres="Carla",
        apellidos="Vega",
        fecha_nacimiento="1990-01-01",
        sexo="F",
    )
    Triaje.objects.create(
        paciente=paciente,
        spo2=98,
        frecuencia_cardiaca=72,
        temperatura=36.7,
        nivel_prioridad=4,
        usuario_enfermeria=user,
    )
    NotaMedica.objects.create(
        paciente=paciente,
        medico=user,
        motivo_consulta="Control",
        contenido="Consulta de control.",
    )

    client.login(username="medico_hist", password="p")
    response = client.get(
        reverse("consulta:historia_clinica", kwargs={"paciente_pk": paciente.pk})
    )

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "Consulta médica" in body
    assert "Triaje" in body
    assert paciente.apellidos in body


@pytest.mark.django_db
def test_historia_clinica_negada_a_no_staff(client):
    """Un usuario sin permiso de consulta no puede ver la historia clínica."""
    paciente = Paciente.objects.create(
        dni="10101010",
        nombres="Sin",
        apellidos="Permiso",
        fecha_nacimiento="1990-01-01",
        sexo="M",
    )
    make_user("don_nadie")
    client.login(username="don_nadie", password="p")
    response = client.get(
        reverse("consulta:historia_clinica", kwargs={"paciente_pk": paciente.pk})
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_listado_y_detalle_visible_a_medico(client):
    group = Group.objects.get(name="Medicos")
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

