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
    def validar_dni(dni, tipo_documento="DNI"):
        """
        Valida el formato del documento de identidad según su tipo.
        Retorna (válido: bool, mensaje: str)
        """
        if not dni:
            return False, "El número de documento es requerido."

        dni = dni.strip()

        if tipo_documento == "DNI":
            if not dni.isdigit() or len(dni) != 8:
                return False, "El DNI debe tener exactamente 8 dígitos numéricos."
        elif tipo_documento == "PAS":
            if len(dni) < 6 or len(dni) > 15:
                return False, "El Pasaporte debe tener entre 6 y 15 caracteres."
        elif tipo_documento == "CE":
            if len(dni) < 8 or len(dni) > 12:
                return False, "El Carné de Extranjería debe tener entre 8 y 12 caracteres."

        # Validación general de caracteres alfanuméricos para otros tipos
        if not dni.replace("-", "").replace(".", "").isalnum():
            return (
                False,
                "El documento contiene caracteres inválidos. Use solo letras y números.",
            )

        return True, "Documento válido."

    @staticmethod
    def normalizar_dni(dni):
        """Normaliza un DNI para comparaciones: strip y upper."""
        if dni is None:
            return dni
        return dni.strip().upper()

    def search(self, q=None):
        """Busqueda sencilla sobre pacientes activos por dni, nombres o apellidos.

        Retorna queryset ordenado por created_at descendente y con usuario_creador
        seleccionado para evitar N+1.
        """
        qs = self.get_activos()
        if not q:
            return qs.order_by("-created_at")

        q = q.strip()
        return (
            qs.filter(
                models.Q(dni__icontains=q)
                | models.Q(nombres__icontains=q)
                | models.Q(apellidos__icontains=q)
            )
            .order_by("-created_at")
        )


class Paciente(AbstractBaseModel):
    """Modelo de Paciente para el módulo de Admisión."""

    TIPO_DOCUMENTO_CHOICES = [
        ("DNI", "DNI"),
        ("PAS", "Pasaporte"),
        ("CE", "Carné de Extranjería"),
    ]

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
    tipo_documento = models.CharField(
        max_length=3,
        choices=TIPO_DOCUMENTO_CHOICES,
        default="DNI",
        verbose_name="Tipo de Documento",
    )
    dni = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name="Número de Documento",
        help_text="DNI, Pasaporte o Carné de Extranjería",
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

        # Validar DNI/Documento
        es_valido, mensaje = PacienteManager.validar_dni(self.dni, self.tipo_documento)
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

    def soft_delete(self):
        """Marcar paciente como inactivo sin eliminar la fila."""
        self.estado = "inactivo"
        # actualizar timestamps mediante save normal
        self.save()

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
