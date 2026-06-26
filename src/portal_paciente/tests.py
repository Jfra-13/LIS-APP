import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from admision.models import Paciente
from consulta.models import NotaMedica

from .ai_service import AIService
from .models import AIChatUsage

User = get_user_model()


class FakeResponse:
    """Minimal stand-in for an httpx.Response in tests."""

    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class AIServiceTests(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            dni="11111111",
            nombres="Ana",
            apellidos="Gomez",
            fecha_nacimiento="1990-01-01",
            sexo="F",
            email="ana@example.com",
        )

    def test_daily_limit_blocks_without_network_or_key(self):
        """Over-quota patients get the limit message, never calling the API."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "k", "AI_MAX_QUESTIONS_PER_DAY": "3"}):
            service = AIService()
            AIChatUsage.objects.create(paciente=self.paciente, count=3)
            with patch("portal_paciente.ai_service.httpx.post") as mock_post:
                reply = service.get_response(self.paciente, "¿Hola?")
            mock_post.assert_not_called()
        self.assertIn("límite", reply)

    def test_missing_api_key_degrades_gracefully(self):
        """No configured key → friendly message, no crash, no network."""
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            service = AIService()
            with patch("portal_paciente.ai_service.httpx.post") as mock_post:
                reply = service.get_response(self.paciente, "¿Hola?")
            mock_post.assert_not_called()
        self.assertIn("no está disponible", reply)

    def test_success_increments_usage_and_injects_diagnosis(self):
        """A successful call counts toward quota and the diagnosis reaches the prompt."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "k"}):
            service = AIService()
            with patch(
                "portal_paciente.ai_service.httpx.post",
                return_value=FakeResponse("Respuesta del asistente"),
            ) as mock_post:
                reply = service.get_response(self.paciente, "¿Qué tengo?", last_diagnosis="J00 - Resfriado")

        self.assertEqual(reply, "Respuesta del asistente")
        usage = AIChatUsage.objects.get(paciente=self.paciente)
        self.assertEqual(usage.count, 1)

        sent_payload = mock_post.call_args.kwargs["json"]
        system_prompt = sent_payload["messages"][0]["content"]
        self.assertIn("J00 - Resfriado", system_prompt)


class AIChatViewTests(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            dni="22222222",
            nombres="Luis",
            apellidos="Ramirez",
            fecha_nacimiento="1985-03-03",
            sexo="M",
            email="luis@example.com",
        )
        # A User (username == dni) is auto-created from the Paciente via signal;
        # the PatientRequiredMixin matches request.user.username against the dni.
        self.user, _ = User.objects.get_or_create(username="22222222")
        self.url = reverse("portal_paciente:ai_chat")

    def test_non_patient_user_cannot_access(self):
        outsider = User.objects.create_user(username="medico1", password="pw")
        self.client.force_login(outsider)
        response = self.client.post(self.url, {"message": "hola"})
        self.assertNotEqual(response.status_code, 200)

    def test_view_uses_only_requesting_patients_diagnosis(self):
        """Security: the prompt is built from the logged-in patient's own data, never another's."""
        NotaMedica.objects.create(
            paciente=self.paciente,
            contenido="nota",
            cie_code="A00",
            cie_short_description="Colera propio",
        )
        # A different patient with a different diagnosis that must never leak.
        otro = Paciente.objects.create(
            dni="33333333",
            nombres="Otra",
            apellidos="Persona",
            fecha_nacimiento="1970-07-07",
            sexo="F",
            email="otra@example.com",
        )
        NotaMedica.objects.create(
            paciente=otro,
            contenido="nota",
            cie_code="Z99",
            cie_short_description="Diagnostico ajeno",
        )

        self.client.force_login(self.user)
        with patch.dict(os.environ, {"GROQ_API_KEY": "k"}), patch(
            "portal_paciente.ai_service.httpx.post",
            return_value=FakeResponse("ok"),
        ) as mock_post:
            response = self.client.post(self.url, {"message": "¿Qué tengo?"})

        self.assertEqual(response.status_code, 200)
        system_prompt = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("Colera propio", system_prompt)
        self.assertNotIn("Diagnostico ajeno", system_prompt)
