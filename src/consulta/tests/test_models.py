import pytest
from django.core.exceptions import ValidationError

from admision.models import Paciente
from core.models import User
from triage.models import Triaje

from consulta.models import NotaMedica


def make_user(username: str) -> User:
    user = User(username=username)
    user.set_password("p")
    user.save()
    return user



@pytest.mark.django_db
def test_crear_nota_medica_persistencia():
    user = make_user("doc")
    paciente = Paciente.objects.create(
        dni="11111111",
        nombres="Paciente",
        apellidos="Prueba",
        fecha_nacimiento="1990-01-01",
        sexo="M",
    )

    tr = Triaje.objects.create(
        paciente=paciente,
        spo2=98,
        frecuencia_cardiaca=60,
        temperatura=36.5,
        usuario_enfermeria=user,
    )

    nota = NotaMedica.objects.create(
        paciente=paciente, triaje=tr, medico=user, contenido="Historia clínica breve"
    )

    assert NotaMedica.objects.filter(pk=nota.pk).exists()
    assert nota.paciente == paciente
    assert nota.triaje == tr
    assert nota.medico == user


@pytest.mark.django_db
def test_triaje_paciente_mismatch_raises_validation_error():
    user = make_user("u2")
    paciente1 = Paciente.objects.create(
        dni="22222222",
        nombres="Paciente1",
        apellidos="Uno",
        fecha_nacimiento="1990-01-01",
        sexo="F",
    )
    paciente2 = Paciente.objects.create(
        dni="33333333",
        nombres="Paciente2",
        apellidos="Dos",
        fecha_nacimiento="1991-01-01",
        sexo="M",
    )

    tr2 = Triaje.objects.create(
        paciente=paciente2,
        spo2=97,
        frecuencia_cardiaca=70,
        temperatura=36.6,
        usuario_enfermeria=user,
    )

    nota = NotaMedica(paciente=paciente1, triaje=tr2, contenido="Nota inválida")

    with pytest.raises(ValidationError):
        nota.full_clean()

