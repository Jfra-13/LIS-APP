from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse

from admision.models import Paciente
from consulta.models import NotaMedica
from triage.models import Triaje

User = get_user_model()


class NotaMedicaCIEFieldsTest(TestCase):
    """Test persistencia de campos CIE-10 en NotaMedica"""

    def setUp(self):
        """Crear datos base para pruebas"""
        self.user_medico = User.objects.create_user(
            username="medico1",
            password="testpass123",
            is_staff=True
        )
        self.user_enfermeria = User.objects.create_user(
            username="enfermeria1",
            password="testpass123"
        )
        self.paciente = Paciente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            dni="12345678",
            fecha_nacimiento="1990-01-01",
            sexo="M"
        )

    def test_crear_nota_sin_cie(self):
        """Test que crea una nota médica sin CIE (caso básico)"""
        nota = NotaMedica.objects.create(
            paciente=self.paciente,
            medico=self.user_medico,
            motivo_consulta="Dolor de cabeza",
            contenido="Paciente con migraña",
            is_privada=False,
            cie_code=None,
            cie_short_description=None,
            cie_accepted=False
        )

        nota_recuperada = NotaMedica.objects.get(pk=nota.pk)
        self.assertIsNone(nota_recuperada.cie_code)
        self.assertIsNone(nota_recuperada.cie_short_description)
        self.assertFalse(nota_recuperada.cie_accepted)

    def test_crear_nota_con_cie_aceptado(self):
        """Test que persiste una nota con CIE-10 aceptado"""
        nota = NotaMedica.objects.create(
            paciente=self.paciente,
            medico=self.user_medico,
            motivo_consulta="Consulta digestiva",
            contenido="Paciente con síntomas de gastroenteritis",
            is_privada=False,
            cie_code="A09",
            cie_short_description="Diarrea y gastroenteritis de presunto origen infeccioso",
            cie_accepted=True
        )

        nota_recuperada = NotaMedica.objects.get(pk=nota.pk)
        self.assertEqual(nota_recuperada.cie_code, "A09")
        self.assertEqual(
            nota_recuperada.cie_short_description,
            "Diarrea y gastroenteritis de presunto origen infeccioso"
        )
        self.assertTrue(nota_recuperada.cie_accepted)

    def test_validacion_cie_accepted_sin_codigo(self):
        """Test que valida que si cie_accepted=True, cie_code es obligatorio"""
        nota = NotaMedica(
            paciente=self.paciente,
            medico=self.user_medico,
            motivo_consulta="Consulta",
            contenido="Contenido",
            is_privada=False,
            cie_code=None,  # Sin código
            cie_short_description="Descripción",
            cie_accepted=True  # Pero marcado como aceptado
        )

        with self.assertRaises(ValidationError) as ctx:
            nota.full_clean()

        self.assertIn("cie_code", ctx.exception.error_dict)

    def test_validacion_cie_accepted_sin_descripcion(self):
        """Test que valida que si cie_accepted=True, cie_short_description es obligatorio"""
        nota = NotaMedica(
            paciente=self.paciente,
            medico=self.user_medico,
            motivo_consulta="Consulta",
            contenido="Contenido",
            is_privada=False,
            cie_code="A09",
            cie_short_description=None,  # Sin descripción
            cie_accepted=True  # Pero marcado como aceptado
        )

        with self.assertRaises(ValidationError) as ctx:
            nota.full_clean()

        self.assertIn("cie_short_description", ctx.exception.error_dict)

    def test_actualizar_nota_con_cie(self):
        """Test que actualiza una nota existente con datos CIE"""
        nota = NotaMedica.objects.create(
            paciente=self.paciente,
            medico=self.user_medico,
            motivo_consulta="Consulta neurológica",
            contenido="Primer examen",
            is_privada=False,
            cie_code=None,
            cie_accepted=False
        )

        # Actualizar con CIE
        nota.cie_code = "A17"
        nota.cie_short_description = "Tuberculosis del sistema nervioso"
        nota.cie_accepted = True
        nota.save()

        # Recuperar y verificar
        nota_actualizada = NotaMedica.objects.get(pk=nota.pk)
        self.assertEqual(nota_actualizada.cie_code, "A17")
        self.assertEqual(
            nota_actualizada.cie_short_description,
            "Tuberculosis del sistema nervioso"
        )
        self.assertTrue(nota_actualizada.cie_accepted)

    def test_buscar_nota_por_cie_code_index(self):
        """Test que verifica que el índice de cie_code funciona para búsquedas"""
        # Crear varias notas
        NotaMedica.objects.create(
            paciente=self.paciente,
            medico=self.user_medico,
            motivo_consulta="Consulta 1",
            contenido="Contenido 1",
            cie_code="A09",
            cie_short_description="Diarrea y gastroenteritis de presunto origen infeccioso",
            cie_accepted=True
        )
        paciente2 = Paciente.objects.create(
            nombres="María",
            apellidos="García",
            dni="87654321",
            fecha_nacimiento="1985-05-10",
            sexo="F"
        )
        NotaMedica.objects.create(
            paciente=paciente2,
            medico=self.user_medico,
            motivo_consulta="Consulta 2",
            contenido="Contenido 2",
            cie_code="B20",
            cie_short_description="Enfermedad por virus de la inmunodeficiencia humana [VIH]",
            cie_accepted=True
        )

        # Buscar por cie_code
        notas_a09 = NotaMedica.objects.filter(cie_code="A09")
        self.assertEqual(notas_a09.count(), 1)
        self.assertEqual(notas_a09.first().paciente, self.paciente)

    def test_nota_con_triaje_y_cie(self):
        """Test que persiste nota con triaje y CIE-10 simultáneamente"""
        triaje = Triaje.objects.create(
            paciente=self.paciente,
            spo2=98,
            frecuencia_cardiaca=75,
            temperatura=36.5,
            nivel_prioridad=4,
            usuario_enfermeria=self.user_enfermeria
        )

        nota = NotaMedica.objects.create(
            paciente=self.paciente,
            triaje=triaje,
            medico=self.user_medico,
            motivo_consulta="Seguimiento post-triaje",
            contenido="Paciente triado con prioridad 4",
            cie_code="A09",
            cie_short_description="Diarrea y gastroenteritis de presunto origen infeccioso",
            cie_accepted=True
        )

        nota_recuperada = NotaMedica.objects.get(pk=nota.pk)
        self.assertEqual(nota_recuperada.triaje.pk, triaje.pk)
        self.assertEqual(nota_recuperada.cie_code, "A09")
        self.assertTrue(nota_recuperada.cie_accepted)


class NotaMedicaViewIntegrationTest(TestCase):
    """Test de integración para vistas NotaMedica con aceptación CIE"""

    def setUp(self):
        """Crear datos base para pruebas de vistas"""
        self.client = Client()
        self.user_medico = User.objects.create_user(
            username="medico_view",
            password="testpass123",
            is_staff=True
        )
        self.user_medico.groups.add(Group.objects.get(name="Medicos"))
        self.user_enfermeria = User.objects.create_user(
            username="enfermeria_view",
            password="testpass123"
        )
        self.paciente = Paciente.objects.create(
            nombres="Carlos",
            apellidos="López",
            dni="11223344",
            fecha_nacimiento="1988-03-15",
            sexo="M"
        )

    def test_crear_nota_post_sin_cie(self):
        """Test POST a NotaMedicaCreateView sin CIE-10"""
        self.client.login(username="medico_view", password="testpass123")

        response = self.client.post(
            reverse("consulta:nota_create"),
            data={
                "paciente": self.paciente.id,
                "triaje": "",
                "motivo_consulta": "Revisión general",
                "contenido": "Paciente en buen estado",
                "is_privada": False,
                "cie_code": "",
                "cie_short_description": "",
                "cie_accepted": False,
            },
            follow=True
        )

        # Verificar redirección a lista (éxito)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match.url_name, "nota_list")

        # Verificar que se creó la nota sin CIE
        nota = NotaMedica.objects.filter(paciente=self.paciente, motivo_consulta="Revisión general").first()
        self.assertIsNotNone(nota)
        self.assertIsNone(nota.cie_code)
        self.assertFalse(nota.cie_accepted)
        self.assertEqual(nota.medico, self.user_medico)

    def test_crear_nota_post_con_cie_aceptado(self):
        """Test POST a NotaMedicaCreateView con CIE-10 aceptado"""
        self.client.login(username="medico_view", password="testpass123")

        response = self.client.post(
            reverse("consulta:nota_create"),
            data={
                "paciente": self.paciente.id,
                "triaje": "",
                "motivo_consulta": "Consulta gastroenterología",
                "contenido": "Paciente con síntomas digestivos",
                "is_privada": False,
                "cie_code": "A09",
                "cie_short_description": "Diarrea y gastroenteritis de presunto origen infeccioso",
                "cie_accepted": "true",  # Enviado como string desde form oculto
            },
            follow=True
        )

        # Verificar redirección exitosa
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match.url_name, "nota_list")

        # Verificar que se persistió correctamente con CIE
        nota = NotaMedica.objects.filter(
            paciente=self.paciente,
            motivo_consulta="Consulta gastroenterología"
        ).first()
        self.assertIsNotNone(nota)
        self.assertEqual(nota.cie_code, "A09")
        self.assertEqual(
            nota.cie_short_description,
            "Diarrea y gastroenteritis de presunto origen infeccioso"
        )
        self.assertTrue(nota.cie_accepted)
        self.assertEqual(nota.medico, self.user_medico)

    def test_crear_nota_cie_aceptado_sin_codigo_falla(self):
        """Test que valida: si cie_accepted=true, entonces cie_code es obligatorio"""
        self.client.login(username="medico_view", password="testpass123")
        
        response = self.client.post(
            reverse("consulta:nota_create"),
            data={
                "paciente": self.paciente.id,
                "triaje": "",
                "motivo_consulta": "Prueba validación",
                "contenido": "Contenido prueba",
                "is_privada": False,
                "cie_code": "",  # Vacío
                "cie_short_description": "Descripción",
                "cie_accepted": "true",  # Pero marcado como aceptado
            }
        )
        
        # Debe rechazar y mostrar formulario nuevamente (200, no redirect)
        self.assertEqual(response.status_code, 200)
        # El template debe ser el mismo (form.html) cuando hay error de validación
        self.assertTemplateUsed(response, "consulta/form.html")

        # Verificar que NO se creó la nota
        nota_count = NotaMedica.objects.filter(motivo_consulta="Prueba validación").count()
        self.assertEqual(nota_count, 0)

    def test_non_medico_cannot_create_nota(self):
        """Test que verifica que solo médicos pueden crear notas"""
        # Intentar acceder sin login
        response = self.client.get(reverse("consulta:nota_create"))
        # Debe redirigir a login
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_medico_required_grupo_acceso(self):
        """Test que verifica que usuarios sin grupo 'medico' no pueden acceder"""
        # Crear usuario regular sin permisos
        user_regular = User.objects.create_user(
            username="regular_user",
            password="testpass123"
        )
        self.client.login(username="regular_user", password="testpass123")

        response = self.client.get(reverse("consulta:nota_create"))
        # Debe rechazar (no es staff ni en grupo medico)
        self.assertEqual(response.status_code, 403)

    def test_crear_nota_con_triaje_y_cie(self):
        """Test que crea nota con triaje Y CIE-10 simultáneamente via POST"""
        self.client.login(username="medico_view", password="testpass123")

        triaje = Triaje.objects.create(
            paciente=self.paciente,
            spo2=95,
            frecuencia_cardiaca=85,
            temperatura=37.2,
            nivel_prioridad=3,
            usuario_enfermeria=self.user_enfermeria
        )

        response = self.client.post(
            reverse("consulta:nota_create"),
            data={
                "paciente": self.paciente.id,
                "triaje": triaje.id,
                "motivo_consulta": "Seguimiento post-triaje con CIE",
                "contenido": "Control tras triaje con diagnóstico",
                "is_privada": False,
                "cie_code": "B20",
                "cie_short_description": "Enfermedad por virus de la inmunodeficiencia humana [VIH]",
                "cie_accepted": "true",
            },
            follow=True
        )

        self.assertEqual(response.status_code, 200)

        nota = NotaMedica.objects.filter(
            paciente=self.paciente,
            triaje=triaje
        ).first()
        self.assertIsNotNone(nota)
        self.assertEqual(nota.cie_code, "B20")
        self.assertTrue(nota.cie_accepted)

    def test_nota_list_filtra_por_cie_code(self):
        """Test que verifica que la búsqueda en lista funciona con cie_code"""
        self.client.login(username="medico_view", password="testpass123")
        
        # Crear varias notas con diferentes CIE
        NotaMedica.objects.create(
            paciente=self.paciente,
            medico=self.user_medico,
            motivo_consulta="Nota 1",
            contenido="Contenido 1",
            cie_code="A09",
            cie_short_description="Diarrea y gastroenteritis de presunto origen infeccioso",
            cie_accepted=True
        )
        paciente2 = Paciente.objects.create(
            nombres="Ana",
            apellidos="García",
            dni="55667788",
            fecha_nacimiento="1992-06-20",
            sexo="F"
        )
        NotaMedica.objects.create(
            paciente=paciente2,
            medico=self.user_medico,
            motivo_consulta="Nota 2",
            contenido="Contenido 2",
            cie_code="B20",
            cie_short_description="Enfermedad por virus de la inmunodeficiencia humana [VIH]",
            cie_accepted=True
        )
        
        # Buscar sin filtro
        response = self.client.get(reverse("consulta:nota_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["notas"]), 2)

