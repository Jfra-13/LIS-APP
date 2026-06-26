import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Paciente, PacienteManager


class PacienteForm(forms.ModelForm):
    """Formulario para crear y editar pacientes."""

    # Non-model field: dialing prefix shown beside the national number. The
    # combined "<prefix> <number>" string is what gets stored in Paciente.telefono.
    telefono_prefijo = forms.CharField(
        required=False,
        initial="+51",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "+51",
                "aria-label": "Prefijo telefónico",
                "data-testid": "telefono-prefijo-input",
                "style": "max-width: 6rem;",
            }
        ),
    )

    class Meta:
        model = Paciente
        fields = [
            "tipo_documento",
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
            "tipo_documento": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                    "aria-label": "Tipo de Documento",
                    "data-testid": "tipo-documento-select",
                }
            ),
            "dni": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Número de documento",
                    "required": True,
                    "aria-label": "Número de Documento",
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
                    "placeholder": "987654321",
                    "aria-label": "Teléfono",
                    "data-testid": "telefono-input",
                    "inputmode": "numeric",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On edit, split the stored "<prefix> <number>" back into the two fields.
        stored = getattr(self.instance, "telefono", "") or ""
        if stored and self.instance.pk:
            parts = stored.split(" ", 1)
            if len(parts) == 2 and parts[0].startswith("+"):
                self.fields["telefono_prefijo"].initial = parts[0]
                self.initial["telefono"] = parts[1]
            else:
                self.initial["telefono"] = stored

    def clean_dni(self):
        """Validar número de documento usando el manager y tipo de documento."""
        dni = self.cleaned_data.get("dni")
        tipo_doc = self.cleaned_data.get("tipo_documento")

        # Normalizar formato
        dni = PacienteManager.normalizar_dni(dni)
        es_valido, mensaje = PacienteManager.validar_dni(dni, tipo_doc)

        if not es_valido:
            raise ValidationError(mensaje)

        # Verificar duplicado
        qs = Paciente.objects.filter(dni=dni)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Ya existe un paciente con este número de documento.")

        return dni

    def clean_nombres(self):
        """Validar nombres (sin números)."""
        nombres = self.cleaned_data.get("nombres", "").strip()
        if not nombres:
            raise ValidationError("Los nombres son requeridos.")
        if any(char.isdigit() for char in nombres):
            raise ValidationError("Los nombres no pueden contener números.")
        if len(nombres) < 2:
            raise ValidationError("Los nombres deben tener al menos 2 caracteres.")
        return nombres

    def clean_apellidos(self):
        """Validar apellidos (sin números)."""
        apellidos = self.cleaned_data.get("apellidos", "").strip()
        if not apellidos:
            raise ValidationError("Los apellidos son requeridos.")
        if any(char.isdigit() for char in apellidos):
            raise ValidationError("Los apellidos no pueden contener números.")
        if len(apellidos) < 2:
            raise ValidationError("Los apellidos deben tener al menos 2 caracteres.")
        return apellidos

    def clean_telefono(self):
        """El número nacional: solo dígitos. El límite de longitud depende del
        prefijo y se valida en clean() (con +51 son 9 dígitos; otros, libre)."""
        telefono = self.cleaned_data.get("telefono", "").strip()
        if telefono and not telefono.isdigit():
            raise ValidationError("El teléfono debe contener solo números.")
        return telefono

    def clean_telefono_prefijo(self):
        """Prefijo en formato +código (1-4 dígitos). Vacío equivale a +51."""
        prefijo = (self.cleaned_data.get("telefono_prefijo") or "").strip()
        if not prefijo:
            return "+51"
        if not re.fullmatch(r"\+\d{1,4}", prefijo):
            raise ValidationError("El prefijo debe tener formato +código (ej. +51).")
        return prefijo

    def clean(self):
        """Aplica el límite de 9 dígitos solo con prefijo +51 y combina
        prefijo + número en el campo telefono que persiste el modelo."""
        cleaned = super().clean()
        telefono = (cleaned.get("telefono") or "").strip()
        prefijo = (cleaned.get("telefono_prefijo") or "+51").strip()
        if telefono:
            if prefijo == "+51" and len(telefono) > 9:
                self.add_error(
                    "telefono",
                    "Con prefijo +51 el teléfono no puede tener más de 9 dígitos.",
                )
            else:
                cleaned["telefono"] = f"{prefijo} {telefono}"
        return cleaned


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
