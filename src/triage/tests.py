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

    def _input(self, spo2=97, fc=80, temp='36.8', red_flag=Triaje.RedFlagChoices.NONE):
        return TriageInput(
            spo2=spo2,
            frecuencia_cardiaca=fc,
            temperatura=Decimal(temp),
            red_flag=red_flag,
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
            ('34.9', 1),
            ('35.0', 2),
            ('35.9', 2),
            ('36.0', 5),
            ('37.9', 5),
            ('38.0', 3),
            ('38.9', 3),
            ('39.0', 2),
            ('40.9', 2),
            ('41.0', 1),
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

    def test_rn03_raises_for_missing_critical_fields(self):
        with self.assertRaises(RN03MissingCriticalDataError):
            self.service.calculate(TriageInput(spo2=None, frecuencia_cardiaca=80, temperatura=Decimal('36.8')))

        with self.assertRaises(RN03MissingCriticalDataError):
            self.service.calculate(TriageInput(spo2=97, frecuencia_cardiaca=None, temperatura=Decimal('36.8')))

        with self.assertRaises(RN03MissingCriticalDataError):
            self.service.calculate(TriageInput(spo2=97, frecuencia_cardiaca=80, temperatura=None))


class TriajeModelAndViewTests(TestCase):
    def setUp(self):
        self.client.force_login(self._create_enfermeria_user())
        self.enfermeria_user = User.objects.get(username='enfermero')

        self.other_user = User.objects.create_user(username='otro', password='pass123')
        self.paciente = Paciente.objects.create(
            dni='55667788',
            nombres='Ana',
            apellidos='Lopez',
            fecha_nacimiento=date(1992, 2, 10),
            sexo='F',
            usuario_creador=self.other_user,
        )

    @staticmethod
    def _create_enfermeria_user():
        user = User.objects.create_user(username='enfermero', password='pass123')
        group, _ = Group.objects.get_or_create(name='Enfermeria')
        user.groups.add(group)
        return user

    def test_create_triaje_success(self):
        payload = {
            'spo2': 98,
            'frecuencia_cardiaca': 82,
            'temperatura': '36.7',
            'red_flag': Triaje.RedFlagChoices.NONE,
            'observaciones': 'Paciente estable.',
        }

        response = self.client.post(
            reverse('triage:triage_create', kwargs={'paciente_pk': self.paciente.pk}),
            payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Triaje.objects.count(), 1)
        triaje = Triaje.objects.first()
        self.assertEqual(triaje.paciente, self.paciente)
        self.assertEqual(triaje.usuario_enfermeria, self.enfermeria_user)
        self.assertEqual(triaje.nivel_prioridad, 5)
        self.assertEqual(triaje.color_manchester, 'Azul')

    def test_form_renders_priority_readonly(self):
        response = self.client.get(reverse('triage:triage_create', kwargs={'paciente_pk': self.paciente.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'readonly')

    def test_create_triaje_missing_critical_data_returns_400(self):
        payload = {
            'spo2': '',
            'frecuencia_cardiaca': 82,
            'temperatura': '36.7',
            'red_flag': Triaje.RedFlagChoices.NONE,
        }
        response = self.client.post(reverse('triage:triage_create', kwargs={'paciente_pk': self.paciente.pk}), payload)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'RN-03', status_code=400)

    def test_non_enfermeria_user_cannot_access_triaje(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse('triage:triage_create', kwargs={'paciente_pk': self.paciente.pk}))
        self.assertEqual(response.status_code, 302)

    def test_model_is_immutable_after_creation(self):
        triaje = Triaje.objects.create(
            paciente=self.paciente,
            spo2=95,
            frecuencia_cardiaca=100,
            temperatura=Decimal('36.5'),
            red_flag=Triaje.RedFlagChoices.NONE,
            nivel_prioridad=5,
            usuario_enfermeria=self.enfermeria_user,
        )

        triaje.temperatura = Decimal('39.0')
        with self.assertRaises(RN01ImmutableTriageError):
            triaje.save()
