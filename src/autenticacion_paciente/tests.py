from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.contrib.auth.models import Group
from admision.models import Paciente
from .tokens import account_activation_token
from .services import enviar_magic_link

User = get_user_model()

class AutenticacionPacienteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="paciente_test",
            email="paciente@test.com",
            password="password123",
            first_name="Paciente",
            last_name="Prueba"
        )
        # Asegurar que el grupo existe
        Group.objects.get_or_create(name='Pacientes')
        
        # Crear un paciente en admision para probar el flujo de solicitud
        self.paciente = Paciente.objects.create(
            dni="87654321",
            nombres="Maria",
            apellidos="Delgado",
            fecha_nacimiento="1995-05-05",
            sexo="F",
            email="maria@example.com"
        )

    def test_token_generation(self):
        """Prueba que se genere un token válido para el usuario."""
        token = account_activation_token.make_token(self.user)
        self.assertTrue(account_activation_token.check_token(self.user, token))

    def test_enviar_magic_link(self):
        """Prueba que el servicio de envío de email funcione y use el mailbox de prueba."""
        success = enviar_magic_link(self.user)
        self.assertTrue(success)
        # Verificar que se "envió" un correo
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/auth-paciente/verificar/", mail.outbox[0].body)

    def test_request_link_view_success(self):
        """Prueba que la vista de solicitud cree el usuario y envíe el link."""
        response = self.client.post(reverse('autenticacion_paciente:request_link'), {'tipo_documento': 'DNI', 'dni': '87654321'})
        self.assertEqual(response.status_code, 302) # Redirect to link_sent
        
        # Verificar que el User fue creado
        user_exists = User.objects.filter(username='87654321').exists()
        self.assertTrue(user_exists)
        user = User.objects.get(username='87654321')
        self.assertEqual(user.email, 'maria@example.com')
        self.assertTrue(user.groups.filter(name='Pacientes').exists())
        
        # Verificar que se envió el email
        self.assertEqual(len(mail.outbox), 1)

    def test_request_link_view_invalid_dni(self):
        """Prueba que la vista muestre error si el DNI no existe en Pacientes."""
        response = self.client.post(reverse('autenticacion_paciente:request_link'), {'tipo_documento': 'DNI', 'dni': '00000000'})
        self.assertEqual(response.status_code, 200)
        # Verificar que el mensaje de error está en el contenido si assertFormError falla
        self.assertContains(response, 'No se encontró un paciente con ese DNI.')

    def test_verify_link_success(self):
        """Prueba que al visitar el link se inicie sesión."""
        token = account_activation_token.make_token(self.user)
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        url = reverse('autenticacion_paciente:verify_link', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        # Bug #1 fix: magic link must redirect to the patient portal, not 'home'
        self.assertRedirects(
            response,
            reverse('portal_paciente:dashboard'),
            fetch_redirect_response=False,
        )

        # Verificar que el usuario está logueado
        self.assertIn('_auth_user_id', self.client.session)

    def test_verify_link_invalid(self):
        """Prueba que un link inválido muestre la página de error."""
        url = reverse('autenticacion_paciente:verify_link', kwargs={'uidb64': 'invalid', 'token': 'invalid'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'autenticacion_paciente/invalid_link.html')
