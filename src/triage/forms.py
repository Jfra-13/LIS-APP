from django import forms
from django.core.exceptions import ValidationError

from .exceptions import RN03MissingCriticalDataError
from .models import Triaje
from .services import TriageCalculatorService, TriageInput


class TriajeForm(forms.ModelForm):
    nivel_prioridad = forms.IntegerField(
        required=False,
        disabled=True,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "readonly": True,
                "aria-label": "Nivel de prioridad (solo lectura)",
            }
        ),
        label="Nivel de prioridad (calculado)",
    )

    class Meta:
        model = Triaje
        fields = [
            "spo2",
            "frecuencia_cardiaca",
            "temperatura",
            "red_flag",
            "observaciones",
        ]
        widgets = {
            "spo2": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 100,
                    "required": True,
                    "placeholder": "Ej. 97",
                }
            ),
            "frecuencia_cardiaca": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 20,
                    "max": 250,
                    "required": True,
                    "placeholder": "Ej. 82",
                }
            ),
            "temperatura": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.1",
                    "min": 30,
                    "max": 45,
                    "required": True,
                    "placeholder": "Ej. 36.8",
                }
            ),
            "red_flag": forms.Select(attrs={"class": "form-select"}),
            "observaciones": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observaciones adicionales de enfermeria",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._calculated_priority = None

        if self.data:
            self._populate_preview_priority()

    def _populate_preview_priority(self):
        triage_input = TriageInput(
            spo2=self._to_int_or_none(self.data.get("spo2")),
            frecuencia_cardiaca=self._to_int_or_none(
                self.data.get("frecuencia_cardiaca")
            ),
            temperatura=self._to_decimal_or_none(self.data.get("temperatura")),
            red_flag=self.data.get("red_flag") or Triaje.RedFlagChoices.NONE,
        )

        try:
            priority = TriageCalculatorService().calculate(triage_input)
            self.fields["nivel_prioridad"].initial = priority
        except RN03MissingCriticalDataError:
            self.fields["nivel_prioridad"].initial = None

    @staticmethod
    def _to_int_or_none(raw_value):
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_decimal_or_none(raw_value):
        if raw_value in (None, ""):
            return None
        try:
            return forms.DecimalField().clean(raw_value)
        except ValidationError:
            return None

    def clean(self):
        cleaned_data = super().clean()
        triage_input = TriageInput(
            spo2=cleaned_data.get("spo2"),
            frecuencia_cardiaca=cleaned_data.get("frecuencia_cardiaca"),
            temperatura=cleaned_data.get("temperatura"),
            red_flag=cleaned_data.get("red_flag") or Triaje.RedFlagChoices.NONE,
        )

        try:
            self._calculated_priority = TriageCalculatorService().calculate(
                triage_input
            )
        except RN03MissingCriticalDataError as exc:
            raise ValidationError(str(exc)) from exc

        self.fields["nivel_prioridad"].initial = self._calculated_priority
        return cleaned_data

    def save(self, commit=True, paciente=None, usuario_enfermeria=None):
        obj = super().save(commit=False)
        obj.nivel_prioridad = self._calculated_priority
        if paciente is not None:
            obj.paciente = paciente
        if usuario_enfermeria is not None:
            obj.usuario_enfermeria = usuario_enfermeria

        if commit:
            obj.save()
        return obj
