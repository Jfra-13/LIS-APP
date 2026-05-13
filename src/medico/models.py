from django.db import models
from django.utils import timezone


class ColaEstado(models.Model):
    """Representa el estado operativo de atención asociado a un Triaje.

    Mantiene una relación OneToOne con `triage.Triaje` y protege la
    inmutabilidad del Triaje al almacenar aquí los cambios operativos.
    Implementa validaciones simples de transición (FSM manual).
    """

    class EstadoChoices(models.TextChoices):
        EN_ESPERA = "EN_ESPERA", "En espera"
        EN_CONSULTORIO = "EN_CONSULTORIO", "En consultorio"
        FINALIZADO = "FINALIZADO", "Finalizado"

    triaje = models.OneToOneField(
        "triage.Triaje",
        on_delete=models.PROTECT,
        related_name="cola_estado",
        blank=True,
    )
    estado = models.CharField(
        max_length=20, choices=EstadoChoices.choices, default=EstadoChoices.EN_ESPERA
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ColaEstado {self.triaje_id} - {self.estado}"

    def can_transition(self, new_estado: str) -> bool:
        """Simple rules for allowed transitions.

        EN_ESPERA -> EN_CONSULTORIO
        EN_CONSULTORIO -> FINALIZADO
        EN_ESPERA -> FINALIZADO (allowed for cancellation/skip)
        """
        current = self.estado
        if current == new_estado:
            return True
        allowed = {
            self.EstadoChoices.EN_ESPERA: {
                self.EstadoChoices.EN_CONSULTORIO,
                self.EstadoChoices.FINALIZADO,
            },
            self.EstadoChoices.EN_CONSULTORIO: {self.EstadoChoices.FINALIZADO},
            self.EstadoChoices.FINALIZADO: set(),
        }
        return new_estado in allowed.get(current, set())

    def set_estado(self, new_estado: str):
        if not self.can_transition(new_estado):
            raise ValueError(f"Invalid transition from {self.estado} to {new_estado}")
        self.estado = new_estado
        self.save()
