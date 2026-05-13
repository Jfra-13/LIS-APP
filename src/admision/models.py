from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import AbstractBaseModel

User = get_user_model()


class PacienteManager(models.Manager):
    """Manager personalizado para Paciente con query optimization."""

    def get_activos(self):
        """Retorna solo pacientes activos con select_related para usuario_creador."""
        return self.filter(estado="activo").select_related("usuario_creador")

    @staticmethod
    def validar_dni(dni):
        """
        Valida el formato del DNI.
        Retorna (válido: bool, mensaje: str)
        """
        if not dni:
            return False, "El DNI es requerido."

        dni = dni.strip()

        if len(dni) < 8 or len(dni) > 20:
            return False, "El DNI debe tener entre 8 y 20 caracteres."

        # Permitir números y letras
        if not dni.replace("-", "").replace(".", "").isalnum():
            return (
                False,
                "El DNI contiene caracteres inválidos. Use solo letras, números, guiones y puntos.",
            )

        return True, "DNI válido."


class Paciente(AbstractBaseModel):
    """Modelo de Paciente para el módulo de Admisión."""

    SEXO_CHOICES = [
        ("M", "Masculino"),
        ("F", "Femenino"),
        ("O", "Otro"),
    ]

    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
    ]

    # Información de identidad
    dni = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name="DNI/Documento de Identidad",
        help_text="Documento nacional de identidad del paciente",
    )
    nombres = models.CharField(max_length=150, verbose_name="Nombres")
    apellidos = models.CharField(max_length=150, verbose_name="Apellidos")

    # Información demográfica
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, verbose_name="Sexo")

    # Información de contacto
    telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Teléfono",
        help_text="Número de contacto del paciente",
    )
    email = models.EmailField(
        blank=True, verbose_name="Email", help_text="Correo electrónico del paciente"
    )
    direccion = models.TextField(
        blank=True,
        verbose_name="Dirección",
        help_text="Dirección de residencia del paciente",
    )

    # Control de estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="activo",
        db_index=True,
        verbose_name="Estado",
    )

    # Auditoría
    usuario_creador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pacientes_creados",
        verbose_name="Usuario Creador",
        editable=False,
    )

    objects = PacienteManager()

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["dni", "-created_at"]),
            models.Index(fields=["estado", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.dni})"

    def clean(self):
        """Validar datos del paciente."""
        super().clean()

        # Validar DNI
        es_valido, mensaje = PacienteManager.validar_dni(self.dni)
        if not es_valido:
            raise ValidationError({"dni": mensaje})

        # Verificar que no exista otro paciente con el mismo DNI (excepto este)
        qs = Paciente.objects.filter(dni=self.dni)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({"dni": "Ya existe un paciente con este DNI."})

        # Validar que fecha de nacimiento no sea en el futuro
        if self.fecha_nacimiento and self.fecha_nacimiento > timezone.now().date():
            raise ValidationError(
                {
                    "fecha_nacimiento": "La fecha de nacimiento no puede ser en el futuro."
                }
            )

    def save(self, *args, **kwargs):
        """Ejecutar validaciones antes de guardar."""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_edad(self):
        """Calcula la edad actual del paciente."""
        hoy = timezone.now().date()
        edad = hoy.year - self.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (
            self.fecha_nacimiento.month,
            self.fecha_nacimiento.day,
        ):
            edad -= 1
        return edad
