import uuid
from django.core.exceptions import ValidationError
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from django.conf import settings

from core.models import AbstractBaseModel

from admision.models import Paciente


class Medicamento(AbstractBaseModel):
    """Catálogo de medicamentos (puede ser persistido o usado como referencia)."""
    nombre = models.CharField(max_length=255, verbose_name="Nombre")
    presentacion = models.CharField(max_length=100, verbose_name="Presentación")
    concentracion = models.CharField(max_length=50, verbose_name="Concentración")

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"

    def __str__(self):
        return f"{self.nombre} ({self.presentacion} - {self.concentracion})"


class NotaMedica(AbstractBaseModel):
    """Ficha clínica narrativa (nota médica) asociada a un paciente y opcionalmente a un triaje."""

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="notas_medicas",
        verbose_name="Paciente",
    )

    # Import triage lazily in validations to avoid circular import at module import time
    triaje = models.ForeignKey(
        "triage.Triaje",
        on_delete=models.PROTECT,
        related_name="notas_medicas",
        null=True,
        blank=True,
        verbose_name="Triaje relacionado",
    )

    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notas_creadas",
        verbose_name="Medico responsable",
    )

    motivo_consulta = models.CharField(max_length=255, blank=True, verbose_name="Motivo de consulta")
    contenido = models.TextField(verbose_name="Contenido clínico")
    is_privada = models.BooleanField(default=False, verbose_name="Privada")

    # Identificador único de receta para el portal del paciente
    receta_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="ID de Receta"
    )

    # Campos para persistencia de selección CIE-10
    cie_code = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Código CIE-10",
        help_text="Código CIE-10 seleccionado (ej: A00, B20, etc.)"
    )
    cie_short_description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Descripción CIE-10",
        help_text="Descripción corta del código CIE-10 seleccionado"
    )
    cie_accepted = models.BooleanField(
        default=False,
        verbose_name="CIE-10 aceptado",
        help_text="Indica si la sugerencia CIE-10 fue aceptada por el médico"
    )

    class EstadoIA(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PROCESANDO = "PROCESANDO", "Procesando"
        LISTO = "LISTO", "Listo"
        ERROR = "ERROR", "Error"

    # Estado del procesamiento asíncrono de IA (RF-06)
    estado_ia = models.CharField(
        max_length=10,
        choices=EstadoIA.choices,
        default=EstadoIA.PENDIENTE,
        db_index=True,
        verbose_name="Estado de procesamiento IA",
        help_text="Estado del análisis NLP en segundo plano",
    )

    # Sugerencias CIE-10 generadas por el motor de IA (RF-07).
    # Separado de cie_code: la IA SUGIERE, el médico CONFIRMA en cie_code.
    cie_suggestions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Sugerencias CIE-10 (IA)",
        help_text="Lista de sugerencias propuestas por el motor de IA (no confirmadas)",
    )

    class Meta:
        verbose_name = "Nota médica"
        verbose_name_plural = "Notas médicas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["paciente", "-created_at"]),
        ]

    def __str__(self):
        return f"NotaMedica {self.paciente.dni} - {self.created_at.isoformat()}"

    def clean(self):
        super().clean()

        if self.triaje is not None:
            from triage.models import Triaje

            triaje = self.triaje
            if not isinstance(triaje, Triaje):
                try:
                    triaje = Triaje.objects.get(pk=triaje)
                except Triaje.DoesNotExist as exc:
                    raise ValidationError({"triaje": "Triaje inválido."}) from exc

            if triaje.paciente.pk != self.paciente.pk:
                raise ValidationError(
                    {"triaje": "El triaje asociado no pertenece al paciente indicado."}
                )

        # Validar consistencia de CIE-10: si está aceptado, debe tener código y descripción
        if self.cie_accepted:
            if not self.cie_code:
                raise ValidationError(
                    {"cie_code": "El código CIE-10 es obligatorio si se acepta la sugerencia."}
                )
            if not self.cie_short_description:
                raise ValidationError(
                    {"cie_short_description": "La descripción CIE-10 es obligatoria si se acepta la sugerencia."}
                )

    def save(self, *args, **kwargs):
        # Asegurar que se genere un receta_id si por alguna razón es nulo
        if not self.receta_id:
            self.receta_id = uuid.uuid4()
            
        # Validar antes de persistir
        self.full_clean()
        super().save(*args, **kwargs)


class Prescripcion(AbstractBaseModel):
    """Vínculo entre una NotaMedica y los medicamentos recetados."""

    nota_medica = models.ForeignKey(
        NotaMedica,
        on_delete=models.CASCADE,
        related_name="prescripciones",
        verbose_name="Nota médica"
    )
    medicamento = models.ForeignKey(
        Medicamento,
        on_delete=models.PROTECT,
        verbose_name="Medicamento"
    )
    dosis = models.CharField(max_length=100, verbose_name="Dosis")
    frecuencia = models.CharField(max_length=100, verbose_name="Frecuencia")
    duracion = models.CharField(max_length=100, verbose_name="Duración")
    instrucciones_adicionales = models.TextField(
        blank=True,
        null=True,
        verbose_name="Instrucciones adicionales"
    )

    class Meta:
        verbose_name = "Prescripción"
        verbose_name_plural = "Prescripciones"

    def __str__(self):
        return f"{self.medicamento.nombre} - {self.dosis}"

