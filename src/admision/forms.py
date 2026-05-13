from django import forms
from django.core.exceptions import ValidationError

from .models import Paciente, PacienteManager


class PacienteForm(forms.ModelForm):
    """Formulario para crear y editar pacientes."""

    class Meta:
        model = Paciente
        fields = [
            "dni",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "sexo",
            "telefono",
            "email",
            "direccion",
        ]
        widgets = {
            "dni": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. 12345678 o 12345678-A",
                    "pattern": r"[0-9A-Za-z.-]{8,20}",
                    "required": True,
                    "aria-label": "DNI o Documento de Identidad",
                    "data-testid": "dni-input",
                }
            ),
            "nombres": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombres del paciente",
                    "required": True,
                    "aria-label": "Nombres",
                    "data-testid": "nombres-input",
                }
            ),
            "apellidos": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Apellidos del paciente",
                    "required": True,
                    "aria-label": "Apellidos",
                    "data-testid": "apellidos-input",
                }
            ),
            "fecha_nacimiento": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                    "required": True,
                    "aria-label": "Fecha de Nacimiento",
                    "data-testid": "fecha-nacimiento-input",
                }
            ),
            "sexo": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                    "aria-label": "Sexo",
                    "data-testid": "sexo-select",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+34 612 345 678",
                    "aria-label": "Teléfono",
                    "data-testid": "telefono-input",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "correo@ejemplo.com",
                    "aria-label": "Email",
                    "data-testid": "email-input",
                }
            ),
            "direccion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Calle, número, ciudad, código postal",
                    "aria-label": "Dirección",
                    "data-testid": "direccion-input",
                }
            ),
        }

    def clean_dni(self):
        """Validar DNI usando el manager."""
        dni = self.cleaned_data.get("dni")
        es_valido, mensaje = PacienteManager.validar_dni(dni)

        if not es_valido:
            raise ValidationError(mensaje)

        # Verificar duplicado (excepto si estamos editando)
        qs = Paciente.objects.filter(dni=dni)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Ya existe un paciente con este DNI.")

        return dni

    def clean_nombres(self):
        """Validar nombres."""
        nombres = self.cleaned_data.get("nombres", "").strip()
        if not nombres:
            raise ValidationError("Los nombres son requeridos.")
        if len(nombres) < 2:
            raise ValidationError("Los nombres deben tener al menos 2 caracteres.")
        return nombres

    def clean_apellidos(self):
        """Validar apellidos."""
        apellidos = self.cleaned_data.get("apellidos", "").strip()
        if not apellidos:
            raise ValidationError("Los apellidos son requeridos.")
        if len(apellidos) < 2:
            raise ValidationError("Los apellidos deben tener al menos 2 caracteres.")
        return apellidos


class PacienteFilterForm(forms.Form):
    """Formulario de búsqueda para listado de pacientes."""

    search = forms.CharField(
        label="Buscar por DNI o Nombres",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingrese DNI o nombres...",
                "autofocus": True,
                "aria-label": "Búsqueda de pacientes",
                "data-testid": "search-input",
                "accesskey": "f",  # Alt+F para focus
            }
        ),
    )
