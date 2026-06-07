from django import forms

from .models import NotaMedica, Prescripcion


class BooleanHiddenInput(forms.HiddenInput):
    """Widget que convierte valores booleanos a string para HiddenInput"""

    def value_from_datadict(self, data, files, name):
        # Buscar el valor en data; si viene como "on" o "true", convertir a True
        value = data.get(name, "")
        if value.lower() in ("on", "true", "1"):
            return True
        return False


class NotaMedicaForm(forms.ModelForm):
    class Meta:
        model = NotaMedica
        fields = [
            "paciente",
            "triaje",
            "motivo_consulta",
            "contenido",
            "is_privada",
            "cie_code",
            "cie_short_description",
            "cie_accepted",
        ]
        widgets = {
            "cie_code": forms.HiddenInput(attrs={"id": "id_cie_code"}),
            "cie_short_description": forms.HiddenInput(attrs={"id": "id_cie_short_description"}),
            "cie_accepted": BooleanHiddenInput(attrs={"id": "id_cie_accepted", "value": "false"}),
        }
        help_texts = {
            "contenido": (
                "Soporta Markdown: # encabezados, **negrita**, *cursiva*, " "- listas. El HTML se ignora por seguridad."
            ),
        }

    def clean(self):
        cleaned = super().clean()
        triaje = cleaned.get("triaje")
        paciente = cleaned.get("paciente")

        if triaje and paciente and triaje.paciente_id != paciente.id:
            raise forms.ValidationError("El triaje seleccionado no pertenece al paciente indicado.")

        # Validar que si se acepta CIE, hay datos
        cie_accepted = cleaned.get("cie_accepted", False)
        cie_code = cleaned.get("cie_code")
        if cie_accepted and not cie_code:
            raise forms.ValidationError("Debe seleccionar un código CIE-10 si acepta la sugerencia.")

        return cleaned


class PrescripcionForm(forms.ModelForm):
    class Meta:
        model = Prescripcion
        fields = ["medicamento", "dosis", "frecuencia", "duracion", "instrucciones_adicionales"]


PrescripcionFormSet = forms.inlineformset_factory(
    NotaMedica, Prescripcion, form=PrescripcionForm, extra=1, can_delete=True
)
