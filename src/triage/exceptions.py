from django.core.exceptions import ValidationError


class RN01ImmutableTriageError(ValidationError):
    """Se lanza cuando se intenta modificar un triaje ya persistido."""


class RN03MissingCriticalDataError(ValueError):
    """Se lanza cuando faltan signos vitales criticos para calcular prioridad."""

    def __init__(self, missing_fields):
        self.missing_fields = missing_fields
        fields = ", ".join(missing_fields)
        super().__init__(
            f"RN-03: Faltan datos criticos para calcular triaje: {fields}."
        )
