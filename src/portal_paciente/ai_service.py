import os

import httpx
from django.utils import timezone

from .models import AIChatUsage

# Groq exposes an OpenAI-compatible REST API, so we call it directly with httpx
# (already a project dependency) instead of pulling in any SDK.
COMPLETIONS_PATH = "/chat/completions"


class AIService:
    """Thin client for the Groq chat API with per-patient daily quotas."""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = os.getenv(
            "GROQ_BASE_URL",
            "https://api.groq.com/openai/v1",
        ).rstrip("/")
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.max_questions = int(os.getenv("AI_MAX_QUESTIONS_PER_DAY", 5))
        self.max_tokens = int(os.getenv("AI_MAX_TOKENS", 500))
        self.timeout = float(os.getenv("AI_TIMEOUT_SECONDS", 30))

    def _usage_for_today(self, paciente):
        usage, _ = AIChatUsage.objects.get_or_create(
            paciente=paciente, fecha=timezone.localdate()
        )
        return usage

    def can_ask(self, paciente):
        usage = self._usage_for_today(paciente)
        return usage.count < self.max_questions, usage.count

    def remaining(self, paciente):
        """Questions the patient still has available today (never negative)."""
        usage = self._usage_for_today(paciente)
        return max(self.max_questions - usage.count, 0)

    def _build_system_prompt(self, last_diagnosis):
        prompt = (
            "Eres 'Doctor Online Groq', un asistente médico experto, compasivo y disponible 24hs, "
            "potenciado por Groq con el modelo Llama 3.3. Tu objetivo es ayudar al paciente a entender "
            "su situación de salud. No reemplazas una consulta médica real. "
            "REGLAS DE RESPUESTA: "
            "1) Responde SIEMPRE breve y directo: máximo 3 o 4 frases, lenguaje simple, sin tecnicismos "
            "innecesarios ni introducciones largas. Ve al punto y, si corresponde, cierra con una "
            "recomendación concreta en una línea. "
            "2) Si te preguntan sobre ti mismo (qué modelo eres, cómo funcionas, quién te creó), "
            "responde con honestidad y brevedad: eres el Doctor Online Groq basado en Llama 3.3. "
            "3) Si el paciente pregunta algo que NO tiene relación con su salud, síntomas, diagnóstico "
            "o notas médicas, respóndele con amabilidad en una frase y reconduce la conversación a su "
            "situación de salud. No te extiendas en temas ajenos a la medicina. "
            "4) Recuerda al paciente, solo si es pertinente, que tiene un máximo de 5 preguntas por día. "
        )
        if last_diagnosis:
            prompt += (
                f"Actualmente, el paciente tiene un diagnóstico reciente de: {last_diagnosis}. "
                "Responde como un especialista en ese diagnóstico específico."
            )
        else:
            prompt += "Responde como un médico general experto."
        return prompt

    def get_response(self, paciente, user_message, last_diagnosis=None):
        # Quota is checked first: a patient over the daily limit gets a clear
        # message without ever touching the network or needing an API key.
        can, _ = self.can_ask(paciente)
        if not can:
            return (
                f"Has alcanzado el límite de {self.max_questions} preguntas por hoy "
                "para cuidar los costos operativos. Volvé a intentar mañana."
            )

        if not self.api_key:
            return (
                "El asistente no está disponible en este momento "
                "(falta configurar la clave de acceso)."
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt(last_diagnosis)},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        try:
            response = httpx.post(
                f"{self.base_url}{COMPLETIONS_PATH}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # network, auth, malformed payload — degrade gracefully
            return f"Lo siento, hubo un problema al conectar con el asistente médico: {exc}"

        usage = self._usage_for_today(paciente)
        usage.count += 1
        usage.save(update_fields=["count"])
        return content
