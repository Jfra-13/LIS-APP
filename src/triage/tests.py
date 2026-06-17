from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from admision.models import Paciente
from core.models import User

from .exceptions import RN01ImmutableTriageError, RN03MissingCriticalDataError
from .models import Triaje
from .services import TriageCalculatorService, TriageInput


class TriageCalculatorServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = TriageCalculatorService()

    def _input(
        self,
        spo2=97,
        fc=80,
        temp="36.8",
        red_flag=Triaje.RedFlagChoices.NONE,
        sistolica=None,
        diastolica=None,
    ):
        return TriageInput(
            spo2=spo2,
            frecuencia_cardiaca=fc,
            temperatura=Decimal(temp),
            red_flag=red_flag,
            presion_sistolica=sistolica,
            presion_diastolica=diastolica,
        )

    def test_spo2_boundaries(self):
        cases = [
            (84, 1),
            (85, 2),
            (89, 2),
            (90, 3),
            (94, 3),
            (95, 5),
        ]
        for spo2, expected in cases:
            with self.subTest(spo2=spo2):
                result = self.service.calculate(self._input(spo2=spo2))
                self.assertEqual(result, expected)

    def test_heart_rate_boundaries(self):
        cases = [
            (39, 1),
            (40, 2),
            (49, 2),
            (50, 3),
            (59, 3),
            (60, 5),
            (100, 5),
            (101, 3),
            (120, 3),
            (121, 2),
            (140, 2),
            (141, 1),
        ]
        for fc, expected in cases:
            with self.subTest(frecuencia_cardiaca=fc):
                result = self.service.calculate(self._input(fc=fc))
                self.assertEqual(result, expected)

    def test_temperature_boundaries(self):
        cases = [
            ("34.9", 1),
            ("35.0", 2),
            ("35.9", 2),
            ("36.0", 5),
            ("37.9", 5),
            ("38.0", 3),
            ("38.9", 3),
            ("39.0", 2),
            ("40.9", 2),
            ("41.0", 1),
        ]
        for temp, expected in cases:
            with self.subTest(temperatura=temp):
                result = self.service.calculate(self._input(temp=temp))
                self.assertEqual(result, expected)

    def test_red_flag_sets_priority_two(self):
        red_flags = [
            Triaje.RedFlagChoices.DOLOR_TORACICO,
            Triaje.RedFlagChoices.DIFICULTAD_RESPIRATORIA,
            Triaje.RedFlagChoices.HEMORRAGIA_ACTIVA,
        ]

        for red_flag in red_flags:
            with self.subTest(red_flag=red_flag):
                result = self.service.calculate(self._input(red_flag=red_flag))
                self.assertEqual(result, 2)

    def test_blood_pressure_systolic_boundaries(self):
        # Signos vitales normales (prioridad base 5) para aislar el efecto de BP.
        cases = [
            (89, 1),  # hipotension / shock
            (90, 5),  # limite inferior normal
            (159, 5),  # normal-alto
            (160, 3),  # HTA estadio 2
            (179, 3),
            (180, 2),  # crisis hipertensiva
            (220, 2),
        ]
        for sistolica, expected in cases:
            with self.subTest(sistolica=sistolica):
                result = self.service.calculate(self._input(sistolica=sistolica))
                self.assertEqual(result, expected)

    def test_blood_pressure_diastolic_boundaries(self):
        cases = [
            (99, 5),
            (100, 3),  # HTA estadio 2
            (119, 3),
            (120, 2),  # crisis hipertensiva
        ]
        for diastolica, expected in cases:
            with self.subTest(diastolica=diastolica):
                result = self.service.calculate(self._input(diastolica=diastolica))
                self.assertEqual(result, expected)

    def test_blood_pressure_takes_most_severe_of_both(self):
        # Sistolica normal (5) + diastolica en crisis (2) -> gana la mas severa.
        result = self.service.calculate(self._input(sistolica=120, diastolica=125))
        self.assertEqual(result, 2)

    def test_blood_pressure_absent_does_not_change_priority(self):
        # Sin presion arterial, la prioridad depende solo del resto de reglas.
        with_bp = self.service.calculate(self._input(sistolica=120, diastolica=80))
        without_bp = self.service.calculate(self._input())
        self.assertEqual(with_bp, without_bp)
        self.assertEqual(without_bp, 5)

    def test_blood_pressure_is_not_critical_for_rn03(self):
        # La presion arterial es opcional: su ausencia NO dispara RN-03.
        result = self.service.calculate(self._input(sistolica=None, diastolica=None))
        self.assertEqual(result, 5)

    def test_rn03_raises_for_missing_critical_fields(self):
        with self.assertRaises(RN03MissingCriticalDataError):
            self.service.calculate(TriageInput(spo2=None, frecuencia_cardiaca=80, temperatura=Decimal("36.8")))

        with self.assertRaises(RN03MissingCriticalDataError):
            self.service.calculate(TriageInput(spo2=97, frecuencia_cardiaca=None, temperatura=Decimal("36.8")))

        with self.assertRaises(RN03MissingCriticalDataError):
            self.service.calculate(TriageInput(spo2=97, frecuencia_cardiaca=80, temperatura=None))


class TriajeModelAndViewTests(TestCase):
    def setUp(self):
        self.client.force_login(self._create_enfermeria_user())
        self.enfermeria_user = User.objects.get(username="enfermero")

        self.other_user = User.objects.create_user(username="otro", password="pass123")
        self.paciente = Paciente.objects.create(
            dni="55667788",
            nombres="Ana",
            apellidos="Lopez",
            fecha_nacimiento=date(1992, 2, 10),
            sexo="F",
            usuario_creador=self.other_user,
        )

    @staticmethod
    def _create_enfermeria_user():
        user = User.objects.create_user(username="enfermero", password="pass123")
        group, _ = Group.objects.get_or_create(name="Enfermeros")
        user.groups.add(group)
        return user

    def test_create_triaje_success(self):
        payload = {
            "spo2": 98,
            "frecuencia_cardiaca": 82,
            "temperatura": "36.7",
            "red_flag": Triaje.RedFlagChoices.NONE,
            "observaciones": "Paciente estable.",
        }

        response = self.client.post(
            reverse("triage:triage_create", kwargs={"paciente_pk": self.paciente.pk}),
            payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Triaje.objects.count(), 1)
        triaje = Triaje.objects.first()
        self.assertEqual(triaje.paciente, self.paciente)
        self.assertEqual(triaje.usuario_enfermeria, self.enfermeria_user)
        self.assertEqual(triaje.nivel_prioridad, 5)
        self.assertEqual(triaje.color_manchester, "Azul")

    def test_create_triaje_with_blood_pressure_elevates_priority(self):
        # Signos vitales normales pero sistolica en shock -> prioridad 1.
        payload = {
            "spo2": 98,
            "frecuencia_cardiaca": 82,
            "temperatura": "36.7",
            "presion_sistolica": 80,
            "presion_diastolica": 50,
            "red_flag": Triaje.RedFlagChoices.NONE,
            "observaciones": "Hipotension.",
        }

        response = self.client.post(
            reverse("triage:triage_create", kwargs={"paciente_pk": self.paciente.pk}),
            payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        triaje = Triaje.objects.get()
        self.assertEqual(triaje.presion_sistolica, 80)
        self.assertEqual(triaje.presion_diastolica, 50)
        self.assertEqual(triaje.nivel_prioridad, 1)

    def test_create_triaje_without_blood_pressure_succeeds(self):
        # La presion arterial es opcional: omitirla no rompe el alta de triaje.
        payload = {
            "spo2": 98,
            "frecuencia_cardiaca": 82,
            "temperatura": "36.7",
            "red_flag": Triaje.RedFlagChoices.NONE,
        }

        response = self.client.post(
            reverse("triage:triage_create", kwargs={"paciente_pk": self.paciente.pk}),
            payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        triaje = Triaje.objects.get()
        self.assertIsNone(triaje.presion_sistolica)
        self.assertIsNone(triaje.presion_diastolica)
        self.assertEqual(triaje.nivel_prioridad, 5)

    def test_form_renders_priority_readonly(self):
        response = self.client.get(reverse("triage:triage_create", kwargs={"paciente_pk": self.paciente.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "readonly")

    def test_create_triaje_missing_critical_data_returns_400(self):
        payload = {
            "spo2": "",
            "frecuencia_cardiaca": 82,
            "temperatura": "36.7",
            "red_flag": Triaje.RedFlagChoices.NONE,
        }
        response = self.client.post(
            reverse("triage:triage_create", kwargs={"paciente_pk": self.paciente.pk}),
            payload,
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "RN-03", status_code=400)

    def test_non_enfermeria_user_cannot_access_triaje(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("triage:triage_create", kwargs={"paciente_pk": self.paciente.pk}))
        self.assertEqual(response.status_code, 302)

    def test_model_is_immutable_after_creation(self):
        triaje = Triaje.objects.create(
            paciente=self.paciente,
            spo2=95,
            frecuencia_cardiaca=100,
            temperatura=Decimal("36.5"),
            red_flag=Triaje.RedFlagChoices.NONE,
            nivel_prioridad=5,
            usuario_enfermeria=self.enfermeria_user,
        )

        triaje.temperatura = Decimal("39.0")
        with self.assertRaises(RN01ImmutableTriageError):
            triaje.save()

    def test_triage_list_hx_request_devuelve_solo_fragmento(self):
        """El poll HTMX devuelve solo las filas (sin <thead>) para swap innerHTML.

        Evita el bug del <tbody> anidado: si devolviéramos la página completa y
        la inyectáramos en el tbody, se apelmazaban las celdas.
        """
        from django.contrib.auth.models import Permission

        self.enfermeria_user.user_permissions.add(
            Permission.objects.get(codename="view_triaje")
        )
        Triaje.objects.create(
            paciente=self.paciente,
            spo2=98,
            frecuencia_cardiaca=82,
            temperatura=Decimal("36.7"),
            red_flag=Triaje.RedFlagChoices.NONE,
            nivel_prioridad=4,
            usuario_enfermeria=self.enfermeria_user,
        )

        full = self.client.get(reverse("triage:triage_list"))
        fragment = self.client.get(
            reverse("triage:triage_list"), HTTP_HX_REQUEST="true"
        )

        self.assertEqual(full.status_code, 200)
        self.assertEqual(fragment.status_code, 200)
        # La página completa trae la tabla con cabecera; el fragmento no.
        self.assertContains(full, "<thead")
        self.assertNotContains(fragment, "<thead")
        # Ambos muestran al paciente en cola.
        self.assertContains(fragment, self.paciente.apellidos)
