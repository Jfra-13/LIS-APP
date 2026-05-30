from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from admision.models import Paciente
from core.models import AbstractBaseModel

from .exceptions import RN01ImmutableTriageError
from .services import TriageCalculatorService, TriageInput

User = get_user_model()


class Triaje(AbstractBaseModel):
    class RedFlagChoices(models.TextChoices):
        NONE = "NONE", "Sin bandera roja"
        DOLOR_TORACICO = "DOLOR_TORACICO", "Dolor toracico"
        DIFICULTAD_RESPIRATORIA = "DIFICULTAD_RESPIRATORIA", "Dificultad respiratoria"
        HEMORRAGIA_ACTIVA = "HEMORRAGIA_ACTIVA", "Hemorragia activa"

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="triajes",
        verbose_name="Paciente",
    )
    spo2 = models.PositiveSmallIntegerField(
        verbose_name="SpO2",
        help_text="Saturacion de oxigeno (%)",
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    frecuencia_cardiaca = models.PositiveSmallIntegerField(
        verbose_name="Frecuencia cardiaca",
        help_text="Latidos por minuto",
        validators=[MinValueValidator(20), MaxValueValidator(250)],
    )
    temperatura = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        verbose_name="Temperatura",
        help_text="Temperatura corporal en Celsius",
        validators=[MinValueValidator(30), MaxValueValidator(45)],
    )
    red_flag = models.CharField(
        max_length=64,
        choices=RedFlagChoices,
        default=RedFlagChoices.NONE,
        verbose_name="Sintoma bandera roja",
    )
    nivel_prioridad = models.SmallIntegerField(
        verbose_name="Nivel de prioridad",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        editable=False,
    )
    observaciones = models.TextField(blank=True, verbose_name="Observaciones clinicas")
    usuario_enfermeria = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="triajes_registrados",
        editable=False,
        verbose_name="Registrado por",
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Triaje"
        verbose_name_plural = "Triajes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["paciente", "-created_at"]),
            models.Index(fields=["nivel_prioridad", "-created_at"]),
        ]

    def __str__(self):
        return f"Triaje {self.paciente.dni} - Nivel {self.nivel_prioridad}"

    @property
    def color_manchester(self):
        colores = {1: "Rojo", 2: "Naranja", 3: "Amarillo", 4: "Verde", 5: "Azul"}
        return colores.get(self.nivel_prioridad, "Desconocido")

    def save(self, *args, **kwargs):
        # Inmutabilidad estricta: no permitir actualizaciones
        if not self._state.adding:
            raise RN01ImmutableTriageError(
                "RN-01: El triaje es inmutable. Debe registrar un re-triaje nuevo."
            )

        # Calcular nivel_prioridad automáticamente si no fue establecido por la capa superior
        if not self.nivel_prioridad:
            # Construir entrada para calculadora
            triage_input = TriageInput(
                spo2=self.spo2,
                frecuencia_cardiaca=self.frecuencia_cardiaca,
                temperatura=self.temperatura,
                red_flag=self.red_flag or self.RedFlagChoices.NONE,
            )
            # Esto puede lanzar RN03MissingCriticalDataError si faltan datos críticos;
            # preferimos que falle temprano y no cree triajes incompletos.
            self.nivel_prioridad = TriageCalculatorService().calculate(triage_input)

        super().save(*args, **kwargs)
