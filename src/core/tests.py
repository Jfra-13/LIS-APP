import uuid

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from admision.models import Paciente
from autenticacion_paciente.tokens import account_activation_token
from core.models import User
from core.roles import ROLE_HOME, Role, get_role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="testuser", groups=(), is_superuser=False):
    """Create a User, optionally assigning Django Groups by name."""
    user = User.objects.create_user(username=username, password="pass")
    user.is_superuser = is_superuser
    user.is_staff = is_superuser
    user.save()
    for group_name in groups:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
    return user


# ---------------------------------------------------------------------------
# Original MVP-0 tests (updated for role-dispatcher behaviour)
# ---------------------------------------------------------------------------

class CoreMvp0Tests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo-pass-123")

    def test_user_uses_uuid_primary_key(self):
        self.assertIsInstance(self.user.id, uuid.UUID)

    def test_landing_redirects_authenticated_users(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("landing"))
        self.assertRedirects(response, reverse("home"))

    def test_home_requires_authentication(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")

    def test_login_flow_works(self):
        # A user with no role lands on no_acceso.html after login dispatch.
        response = self.client.post(
            reverse("login"),
            {"username": "demo", "password": "demo-pass-123"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)


# ---------------------------------------------------------------------------
# 1. get_role unit tests
# ---------------------------------------------------------------------------

class GetRoleTests(TestCase):
    def test_superuser_returns_superadmin(self):
        user = make_user("su", is_superuser=True)
        self.assertEqual(get_role(user), Role.SUPERADMIN)

    def test_medicos_group_returns_medico(self):
        user = make_user("med", groups=("Medicos",))
        self.assertEqual(get_role(user), Role.MEDICO)

    def test_enfermeros_group_returns_enfermero(self):
        user = make_user("enf", groups=("Enfermeros",))
        self.assertEqual(get_role(user), Role.ENFERMERO)

    def test_admision_group_returns_admision(self):
        user = make_user("adm", groups=("Admision",))
        self.assertEqual(get_role(user), Role.ADMISION)

    def test_pacientes_group_returns_paciente(self):
        user = make_user("pac", groups=("Pacientes",))
        self.assertEqual(get_role(user), Role.PACIENTE)

    def test_priority_medico_over_enfermero(self):
        # User in both Medicos and Enfermeros → MEDICO wins
        user = make_user("multi", groups=("Medicos", "Enfermeros"))
        self.assertEqual(get_role(user), Role.MEDICO)

    def test_no_group_returns_none(self):
        user = make_user("nobody")
        self.assertIsNone(get_role(user))

    def test_anonymous_returns_none(self):
        from django.contrib.auth.models import AnonymousUser
        self.assertIsNone(get_role(AnonymousUser()))


# ---------------------------------------------------------------------------
# 2. Home dispatcher — each role redirects to its own dashboard
# ---------------------------------------------------------------------------

class HomeDispatchTests(TestCase):
    def _assert_home_redirects_to(self, user, expected_url_name, url_kwargs=None):
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        expected = reverse(expected_url_name, kwargs=url_kwargs or {})
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    def test_superadmin_dispatched_to_dashboard_admin(self):
        user = make_user("su", is_superuser=True)
        self._assert_home_redirects_to(user, "dashboard_admin")

    def test_medico_dispatched_to_dashboard_medico(self):
        user = make_user("med", groups=("Medicos",))
        self._assert_home_redirects_to(user, "dashboard_medico")

    def test_enfermero_dispatched_to_dashboard_enfermero(self):
        user = make_user("enf", groups=("Enfermeros",))
        self._assert_home_redirects_to(user, "dashboard_enfermero")

    def test_admision_dispatched_to_dashboard_admision(self):
        user = make_user("adm", groups=("Admision",))
        self._assert_home_redirects_to(user, "dashboard_admision")

    def test_paciente_dispatched_to_portal_dashboard(self):
        user = make_user("pac", groups=("Pacientes",))
        self._assert_home_redirects_to(user, "portal_paciente:dashboard")

    def test_no_role_renders_no_acceso(self):
        user = make_user("nobody")
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/no_acceso.html")


# ---------------------------------------------------------------------------
# 3. Cross-role 403 — wrong role gets PermissionDenied
# ---------------------------------------------------------------------------

class CrossRole403Tests(TestCase):
    def test_medico_cannot_access_dashboard_admision(self):
        user = make_user("med", groups=("Medicos",))
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard_admision"))
        self.assertEqual(response.status_code, 403)

    def test_admision_cannot_access_dashboard_medico(self):
        user = make_user("adm", groups=("Admision",))
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard_medico"))
        self.assertEqual(response.status_code, 403)

    def test_enfermero_cannot_access_dashboard_admin(self):
        user = make_user("enf", groups=("Enfermeros",))
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard_admin"))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_redirected_to_login_on_dashboard(self):
        response = self.client.get(reverse("dashboard_medico"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])


# ---------------------------------------------------------------------------
# 4. Patient isolation
# ---------------------------------------------------------------------------

_PATIENT_DNI = "12345678"  # 8 numeric digits — satisfies Paciente model validation


class PatientIsolationTests(TestCase):
    def setUp(self):
        self.paciente_user = make_user(_PATIENT_DNI, groups=("Pacientes",))
        self.medico_user = make_user("medico01", groups=("Medicos",))
        # Create a matching Paciente record so PatientRequiredMixin passes
        Paciente.objects.create(
            dni=_PATIENT_DNI,
            nombres="Test",
            apellidos="Paciente",
            fecha_nacimiento="1990-01-01",
            sexo="M",
        )

    def test_paciente_cannot_access_dashboard_medico(self):
        self.client.force_login(self.paciente_user)
        response = self.client.get(reverse("dashboard_medico"))
        self.assertEqual(response.status_code, 403)

    def test_medico_cannot_access_portal_paciente_dashboard(self):
        # Medico has no Paciente record → PatientRequiredMixin blocks (redirect to login, not 200)
        self.client.force_login(self.medico_user)
        response = self.client.get(reverse("portal_paciente:dashboard"))
        # Should NOT be 200 — either 302 (login redirect) or 403
        self.assertNotEqual(response.status_code, 200)

    def test_paciente_can_access_portal_dashboard(self):
        self.client.force_login(self.paciente_user)
        response = self.client.get(reverse("portal_paciente:dashboard"))
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# 5. role=None: authenticated user with no role → no_acceso.html
# ---------------------------------------------------------------------------

class NoRoleTests(TestCase):
    def test_authenticated_no_role_gets_no_acceso_template(self):
        user = make_user("orphan")
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/no_acceso.html")


# ---------------------------------------------------------------------------
# 6. Magic link: LoginFromLinkView success → redirects to portal_paciente:dashboard
# ---------------------------------------------------------------------------

class MagicLinkRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="87654321",
            email="patient@example.com",
            password="unused",
        )
        group, _ = Group.objects.get_or_create(name="Pacientes")
        self.user.groups.add(group)

    def test_valid_magic_link_redirects_to_portal_dashboard(self):
        token = account_activation_token.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse(
            "autenticacion_paciente:verify_link",
            kwargs={"uidb64": uid, "token": token},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("portal_paciente:dashboard"),
            fetch_redirect_response=False,
        )
        # Confirm session is authenticated
        self.assertIn("_auth_user_id", self.client.session)

    def test_invalid_magic_link_shows_error_template(self):
        url = reverse(
            "autenticacion_paciente:verify_link",
            kwargs={"uidb64": "bad", "token": "bad"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "autenticacion_paciente/invalid_link.html")


# ---------------------------------------------------------------------------
# 7. Fase C — Navigation context processor and shell smoke tests
# ---------------------------------------------------------------------------

class NavigationContextTests(TestCase):
    """
    Verify that each role's dashboard response contains the correct nav labels
    and does NOT contain labels belonging to other roles.
    """

    def _get_dashboard(self, user, url_name):
        self.client.force_login(user)
        return self.client.get(reverse(url_name))

    # --- Médico ---

    def test_medico_nav_contains_cola_atencion(self):
        user = make_user("med2", groups=("Medicos",))
        response = self._get_dashboard(user, "dashboard_medico")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cola de atención")

    def test_medico_nav_contains_notas_clinicas(self):
        user = make_user("med3", groups=("Medicos",))
        response = self._get_dashboard(user, "dashboard_medico")
        self.assertContains(response, "Notas clínicas")

    def test_medico_nav_does_not_contain_admision_item(self):
        user = make_user("med4", groups=("Medicos",))
        response = self._get_dashboard(user, "dashboard_medico")
        # "Pacientes" sidebar link belongs to Admisión — médico must not see it.
        self.assertNotContains(response, ">Pacientes<")

    # --- Admisión ---

    def test_admision_nav_contains_pacientes(self):
        user = make_user("adm2", groups=("Admision",))
        response = self._get_dashboard(user, "dashboard_admision")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pacientes")

    def test_admision_nav_does_not_contain_medico_items(self):
        user = make_user("adm3", groups=("Admision",))
        response = self._get_dashboard(user, "dashboard_admision")
        self.assertNotContains(response, "Cola de atención")
        self.assertNotContains(response, "Notas clínicas")

    # --- Enfermero ---

    def test_enfermero_nav_contains_triaje(self):
        user = make_user("enf2", groups=("Enfermeros",))
        response = self._get_dashboard(user, "dashboard_enfermero")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Triaje")

    # --- Anonymous landing ---

    def test_anonymous_landing_returns_200(self):
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)


class ShellSmokeTests(TestCase):
    """
    Verify that existing app pages still render (200) inside the new shell
    without template errors.
    """

    def setUp(self):
        # Médico user
        self.medico = make_user("medico_smoke", groups=("Medicos",))
        # Admisión user
        self.admision = make_user("admision_smoke", groups=("Admision",))
        # Enfermero user
        self.enfermero = make_user("enfermero_smoke", groups=("Enfermeros",))

    def test_medico_cola_atencion_renders_in_shell(self):
        self.client.force_login(self.medico)
        response = self.client.get(reverse("medico:cola_atencion"))
        self.assertEqual(response.status_code, 200)

    def test_admision_paciente_list_renders_in_shell(self):
        self.client.force_login(self.admision)
        response = self.client.get(reverse("admision:paciente_list"))
        self.assertEqual(response.status_code, 200)

    def test_enfermero_triage_list_renders_in_shell(self):
        self.client.force_login(self.enfermero)
        response = self.client.get(reverse("triage:triage_list"))
        self.assertEqual(response.status_code, 200)
