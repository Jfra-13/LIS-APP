from django import forms

from admision.models import Paciente


class RequestLoginLinkForm(forms.Form):
    tipo_documento = forms.ChoiceField(
        label="Tipo de documento",
        choices=Paciente.TIPO_DOCUMENTO_CHOICES,
        initial="DNI",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    dni = forms.CharField(
        label="Número de documento",
        max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "Ingresa tu documento"}),
    )

    def clean_dni(self):
        dni = (self.cleaned_data.get("dni") or "").strip()
        tipo = self.cleaned_data.get("tipo_documento")
        if tipo == "DNI" and (not dni.isdigit() or len(dni) != 8):
            raise forms.ValidationError("El DNI debe tener exactamente 8 dígitos.")
        return dni
