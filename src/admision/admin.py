from django.contrib import admin

from .models import Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    """Admin para gestionar pacientes."""

    model = Paciente
    list_display = (
        "dni",
        "nombres",
        "apellidos",
        "sexo",
        "estado",
        "created_at",
        "usuario_creador",
    )
    list_filter = ("estado", "sexo", "created_at")
    search_fields = ("dni", "nombres", "apellidos", "email", "telefono")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "usuario_creador")

    fieldsets = (
        ("Información de Identidad", {"fields": ("id", "dni", "nombres", "apellidos")}),
        ("Información Demográfica", {"fields": ("fecha_nacimiento", "sexo")}),
        ("Información de Contacto", {"fields": ("telefono", "email", "direccion")}),
        ("Control de Estado", {"fields": ("estado", "usuario_creador")}),
        (
            "Auditoría",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        """Asignar usuario_creador si es nuevo."""
        if not change:
            obj.usuario_creador = request.user
        super().save_model(request, obj, form, change)
