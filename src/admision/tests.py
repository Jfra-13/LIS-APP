import time
import uuid
from datetime import date

from django.contrib.auth.models import Group
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from core.models import User
from .models import Paciente, PacienteManager


# ===== PRUEBAS UNITARIAS DEL MODELO =====


class PacienteModelTests(TestCase):
    """Pruebas unitarias para el modelo Paciente."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.user = User.objects.create_user(username="testadmin", password="test123", is_superuser=True)
        self.paciente_data = {
            "tipo_documento": "DNI",
            "dni": "12345678",
            "nombres": "Juan",
            "apellidos": "Pérez",
            "fecha_nacimiento": date(1990, 1, 15),
            "sexo": "M",
            "telefono": "+34 612 345 678",
            "email": "juan@example.com",
            "direccion": "Calle Principal 123, Madrid",
            "usuario_creador": self.user,
        }

    def test_paciente_creacion_exitosa(self):
        """Verificar que se crea un paciente correctamente."""
        paciente = Paciente.objects.create(**self.paciente_data)
        self.assertIsNotNone(paciente.id)
        self.assertIsInstance(paciente.id, uuid.UUID)
        self.assertEqual(paciente.dni, "12345678")
        self.assertEqual(paciente.nombres, "Juan")
        self.assertEqual(paciente.estado, "activo")

    def test_dni_unico(self):
        """Verificar que DNI es único."""
        Paciente.objects.create(**self.paciente_data)

        # Intentar crear otro con el mismo DNI
        with self.assertRaises(Exception):
            Paciente.objects.create(**self.paciente_data)

    def test_dni_validacion_formato(self):
        """Probar validador de DNI con diferentes formatos."""
        # DNI válido
        es_valido, msg = PacienteManager.validar_dni("12345678", "DNI")
        self.assertTrue(es_valido)

        # DNI muy corto
        es_valido, msg = PacienteManager.validar_dni("1234567", "DNI")
        self.assertFalse(es_valido)

        # DNI con letra (inválido para tipo DNI)
        es_valido, msg = PacienteManager.validar_dni("1234567A", "DNI")
        self.assertFalse(es_valido)

        # Pasaporte válido
        es_valido, msg = PacienteManager.validar_dni("ABC123456", "PAS")
        self.assertTrue(es_valido)

        # CE válido
        es_valido, msg = PacienteManager.validar_dni("001234567", "CE")
        self.assertTrue(es_valido)

    def test_campos_requeridos(self):
        """Verificar que campos requeridos lanzan error si faltan."""
        from django.core.exceptions import ValidationError

        # Falta DNI
        paciente = Paciente(
            nombres="Juan",
            apellidos="Pérez",
            fecha_nacimiento=date(1990, 1, 15),
            sexo="M",
            usuario_creador=self.user,
        )
        with self.assertRaises(ValidationError):
            paciente.save()

    def test_usuario_creador_asignado(self):
        """Verificar que usuario_creador se guarda correctamente."""
        paciente = Paciente.objects.create(**self.paciente_data)
        self.assertEqual(paciente.usuario_creador, self.user)

    def test_hereda_timestamps(self):
        """Verificar que created_at se asigna en creación."""
        antes = timezone.now()
        paciente = Paciente.objects.create(**self.paciente_data)
        despues = timezone.now()

        self.assertTrue(antes <= paciente.created_at <= despues)
        self.assertTrue(antes <= paciente.updated_at <= despues)

    def test_get_edad(self):
        """Verificar cálculo de edad."""
        hoy = timezone.now().date()

        # Paciente de 30 años cumplidos
        paciente = Paciente.objects.create(
            **{
                **self.paciente_data,
                "dni": "87654321",
                "fecha_nacimiento": hoy.replace(year=hoy.year - 30),
            }
        )
        self.assertEqual(paciente.get_edad(), 30)

        # Paciente que cumple años hoy
        paciente2 = Paciente.objects.create(
            **{
                **self.paciente_data,
                "dni": "11111111",
                "fecha_nacimiento": hoy.replace(year=hoy.year - 25),
            }
        )
        self.assertEqual(paciente2.get_edad(), 25)


class PacienteManagerTests(TestCase):
    """Pruebas unitarias para PacienteManager."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.user = User.objects.create_user(username="testadmin", password="test123")
        self.paciente_data = {
            "nombres": "Juan",
            "apellidos": "Pérez",
            "fecha_nacimiento": date(1990, 1, 15),
            "sexo": "M",
            "usuario_creador": self.user,
        }

    def test_get_activos_filtra_inactivos(self):
        """Verificar que get_activos() solo retorna pacientes activos."""
        # Crear pacientes activos e inactivos
        pacientes_activos = []
        for i in range(3):
            p = Paciente.objects.create(
                **{**self.paciente_data, "dni": f"1234567{i}", "estado": "activo"}
            )
            pacientes_activos.append(p)

        for i in range(3, 5):
            Paciente.objects.create(
                **{**self.paciente_data, "dni": f"1234567{i}", "estado": "inactivo"}
            )

        # Verificar que get_activos retorna solo 3
        activos = list(Paciente.objects.get_activos())
        self.assertEqual(len(activos), 3)
        for p in activos:
            self.assertEqual(p.estado, "activo")

    def test_select_related_usuario_creador(self):
        """Verificar que get_activos usa select_related sin N+1."""
        # Crear varios pacientes
        for i in range(5):
            Paciente.objects.create(
                **{**self.paciente_data, "dni": f"1234567{i}", "estado": "activo"}
            )

        # Contar queries con select_related
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as context:
            pacientes = list(Paciente.objects.get_activos())
            # Acceder a usuario_creador no debe generar queries adicionales
            for p in pacientes:
                _ = p.usuario_creador

        # Debe haber como máximo 1-2 queries (1 para Paciente, 0 para usuario_creador)
        self.assertLessEqual(len(context), 2, f"Queries ejecutadas: {len(context)}")


# ===== PRUEBAS DE VISTAS (CBV) =====


class PacienteListViewTests(TestCase):
    """Pruebas para PacienteListView."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.client = Client()
        self.user_admin = User.objects.create_user(username="admin", password="pass123", is_superuser=True)
        self.user_normal = User.objects.create_user(username="user", password="pass123")

        # Crear grupo de Técnicos Administrativos
        self.grupo_admin, _ = Group.objects.get_or_create(
            name="Tecnicos_Administrativos"
        )
        self.user_admin.groups.add(self.grupo_admin)

        # Crear pacientes
        self.paciente_data = {
            "nombres": "Juan",
            "apellidos": "Pérez",
            "fecha_nacimiento": date(1990, 1, 15),
            "sexo": "M",
            "usuario_creador": self.user_admin,
        }

        for i in range(5):
            Paciente.objects.create(
                **{**self.paciente_data, "dni": f"1234567{i}", "estado": "activo"}
            )

        for i in range(5, 7):
            Paciente.objects.create(
                **{**self.paciente_data, "dni": f"1234567{i}", "estado": "inactivo"}
            )

    def test_lista_requiere_login(self):
        """Verificar que listado requiere autenticación."""
        response = self.client.get(reverse("admision:paciente_list"))
        self.assertNotEqual(response.status_code, 200)  # No debe ser 200 sin login

    def test_lista_requiere_grupo_admin(self):
        """Verificar que listado requiere grupo Técnicos Administrativos."""
        self.client.force_login(self.user_normal)
        response = self.client.get(reverse("admision:paciente_list"))
        self.assertNotEqual(response.status_code, 200)  # Debe rechazar

    def test_lista_solo_muestra_activos(self):
        """Verificar que solo muestra pacientes activos."""
        self.client.force_login(self.user_admin)
        response = self.client.get(reverse("admision:paciente_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["pacientes"]), 5)

    def test_busqueda_por_dni(self):
        """Verificar búsqueda por DNI."""
        self.client.force_login(self.user_admin)
        response = self.client.get(
            reverse("admision:paciente_list"), {"search": "12345670"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["pacientes"]), 1)

    def test_busqueda_por_nombres(self):
        """Verificar búsqueda por nombres."""
        self.client.force_login(self.user_admin)
        response = self.client.get(
            reverse("admision:paciente_list"), {"search": "Juan"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["pacientes"]), 5)

    def test_paginacion_50_elementos(self):
        """Verificar paginación."""
        self.client.force_login(self.user_admin)

        # Crear 55 pacientes activos
        for i in range(100, 155):
            Paciente.objects.create(
                **{**self.paciente_data, "dni": f"{i:08d}", "estado": "activo"}
            )

        response = self.client.get(reverse("admision:paciente_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["pacientes"]), 50)


class PacienteCreateViewTests(TestCase):
    """Pruebas para PacienteCreateView."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.client = Client()
        self.user_admin = User.objects.create_user(username="admin", password="pass123", is_superuser=True)
        self.user_normal = User.objects.create_user(username="user", password="pass123")

        self.grupo_admin, _ = Group.objects.get_or_create(
            name="Tecnicos_Administrativos"
        )
        self.user_admin.groups.add(self.grupo_admin)

        self.form_data = {
            "tipo_documento": "DNI",
            "dni": "12345678",
            "nombres": "Juan",
            "apellidos": "Pérez",
            "fecha_nacimiento": "1990-01-15",
            "sexo": "M",
            "telefono": "+34 612 345 678",
            "email": "juan@example.com",
            "direccion": "Calle Principal 123",
        }

    def test_crear_sin_grupo_admin(self):
        """Verificar que solo admins pueden crear."""
        self.client.force_login(self.user_normal)
        response = self.client.post(reverse("admision:paciente_create"), self.form_data)
        self.assertNotEqual(response.status_code, 200)

    def test_crear_con_datos_validos(self):
        """Verificar creación con datos válidos."""
        self.client.force_login(self.user_admin)
        response = self.client.post(reverse("admision:paciente_create"), self.form_data)
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertEqual(Paciente.objects.count(), 1)

    def test_crear_asigna_usuario_creador(self):
        """Verificar que se asigna usuario_creador."""
        self.client.force_login(self.user_admin)
        self.client.post(reverse("admision:paciente_create"), self.form_data)
        paciente = Paciente.objects.first()
        self.assertEqual(paciente.usuario_creador, self.user_admin)

    def test_crear_dni_duplicado_falla(self):
        """Verificar que DNI duplicado falla."""
        # Crear primer paciente
        Paciente.objects.create(
            tipo_documento="DNI",
            dni="12345678",
            nombres="Juan",
            apellidos="Pérez",
            fecha_nacimiento=date(1990, 1, 15),
            sexo="M",
            usuario_creador=self.user_admin,
        )

        # Intentar crear otro con mismo DNI
        self.client.force_login(self.user_admin)
        response = self.client.post(reverse("admision:paciente_create"), self.form_data)
        self.assertEqual(response.status_code, 200)  # Re-render del formulario
        self.assertContains(response, "Ya existe un paciente con este número de documento.")

    def test_response_time_menor_1_5_segundos(self):
        """Verificar que tiempo de respuesta < 1.5 segundos."""
        self.client.force_login(self.user_admin)

        inicio = time.perf_counter()
        response = self.client.post(reverse("admision:paciente_create"), self.form_data)
        tiempo_total = time.perf_counter() - inicio

        self.assertLess(tiempo_total, 1.5, f"Tiempo: {tiempo_total:.3f}s > 1.5s")


class PacienteDetailViewTests(TestCase):
    """Pruebas para PacienteDetailView."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.client = Client()
        self.user_admin = User.objects.create_user(username="admin", password="pass123", is_superuser=True)

        self.grupo_admin, _ = Group.objects.get_or_create(
            name="Tecnicos_Administrativos"
        )
        self.user_admin.groups.add(self.grupo_admin)

        self.paciente = Paciente.objects.create(
            dni="12345678",
            nombres="Juan",
            apellidos="Pérez",
            fecha_nacimiento=date(1990, 1, 15),
            sexo="M",
            usuario_creador=self.user_admin,
        )

    def test_ver_detalles_paciente(self):
        """Verificar que se pueden ver detalles."""
        self.client.force_login(self.user_admin)
        response = self.client.get(
            reverse("admision:paciente_detail", kwargs={"pk": self.paciente.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paciente"], self.paciente)


class PacienteUpdateViewTests(TestCase):
    """Pruebas para PacienteUpdateView."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.client = Client()
        self.user_admin = User.objects.create_user(username="admin", password="pass123", is_superuser=True)
        self.user_normal = User.objects.create_user(username="user", password="pass123")

        self.grupo_admin, _ = Group.objects.get_or_create(
            name="Tecnicos_Administrativos"
        )
        self.user_admin.groups.add(self.grupo_admin)

        self.paciente = Paciente.objects.create(
            dni="12345678",
            nombres="Juan",
            apellidos="Pérez",
            fecha_nacimiento=date(1990, 1, 15),
            sexo="M",
            usuario_creador=self.user_admin,
        )

        self.form_data = {
            "tipo_documento": "DNI",
            "dni": "12345678",
            "nombres": "Juan",
            "apellidos": "García",  # Cambio
            "fecha_nacimiento": "1990-01-15",
            "sexo": "M",
        }

    def test_actualizar_sin_grupo_admin(self):
        """Verificar que solo admins pueden actualizar."""
        self.client.force_login(self.user_normal)
        response = self.client.post(
            reverse("admision:paciente_update", kwargs={"pk": self.paciente.pk}),
            self.form_data,
        )
        self.assertNotEqual(response.status_code, 200)

    def test_actualizar_exitoso(self):
        """Verificar actualización exitosa."""
        self.client.force_login(self.user_admin)
        response = self.client.post(
            reverse("admision:paciente_update", kwargs={"pk": self.paciente.pk}),
            self.form_data,
        )
        self.assertEqual(response.status_code, 302)  # Redirect

        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.apellidos, "García")


class PacienteDeleteViewTests(TestCase):
    """Pruebas para PacienteDeleteView (soft delete)."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.client = Client()
        self.user_admin = User.objects.create_user(username="admin", password="pass123", is_superuser=True)
        self.user_normal = User.objects.create_user(username="user", password="pass123")

        self.grupo_admin, _ = Group.objects.get_or_create(
            name="Tecnicos_Administrativos"
        )
        self.user_admin.groups.add(self.grupo_admin)

        self.paciente = Paciente.objects.create(
            dni="12345678",
            nombres="Juan",
            apellidos="Pérez",
            fecha_nacimiento=date(1990, 1, 15),
            sexo="M",
            usuario_creador=self.user_admin,
        )

    def test_delete_no_borra_fila(self):
        """Verificar que soft delete no borra la fila."""
        paciente_id = self.paciente.pk

        self.client.force_login(self.user_admin)
        response = self.client.post(
            reverse("admision:paciente_delete", kwargs={"pk": self.paciente.pk})
        )
        self.assertEqual(response.status_code, 302)

        # Verificar que fila aún existe
        self.assertTrue(Paciente.objects.filter(pk=paciente_id).exists())

        # Verificar que estado cambió a inactivo
        paciente_actualizado = Paciente.objects.get(pk=paciente_id)
        self.assertEqual(paciente_actualizado.estado, "inactivo")


# ===== PRUEBAS DE FORMULARIOS =====


class PacienteFormTests(TestCase):
    """Pruebas para PacienteForm."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.form_data = {
            "tipo_documento": "DNI",
            "dni": "12345678",
            "nombres": "Juan",
            "apellidos": "Pérez",
            "fecha_nacimiento": "1990-01-15",
            "sexo": "M",
        }

    def test_form_campos_requeridos(self):
        """Verificar que campos requeridos son validados."""
        from .forms import PacienteForm

        # Sin DNI
        data = {**self.form_data}
        del data["dni"]
        form = PacienteForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("dni", form.errors)

    def test_form_limpia_dni_valido(self):
        """Verificar que DNI válido pasa validación."""
        from .forms import PacienteForm

        form = PacienteForm(self.form_data)
        self.assertTrue(form.is_valid())

    def test_form_rechaza_nombres_con_numeros(self):
        """Verificar que nombres no pueden tener números."""
        from .forms import PacienteForm
        data = {**self.form_data, "nombres": "Juan123"}
        form = PacienteForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("nombres", form.errors)
