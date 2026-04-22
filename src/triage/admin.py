from django.contrib import admin
from .models import Paciente, RegistroTriage


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    # Columnas que se verán en la tabla principal
    list_display = ('dni', 'apellidos', 'nombre', 'fecha_nacimiento', 'fecha_registro')
    # Agrega una barra de búsqueda por DNI o Apellidos
    search_fields = ('dni', 'apellidos', 'nombre')
    # Ordenar alfabéticamente por defecto
    ordering = ('apellidos', 'nombre')


@admin.register(RegistroTriage)
class RegistroTriageAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'nivel_asignado', 'fecha_ingreso', 'procesado_por_ia')
    # Agrega un panel lateral para filtrar rápidamente
    list_filter = ('nivel_asignado', 'procesado_por_ia', 'fecha_ingreso')
    search_fields = ('paciente__dni', 'paciente__apellidos')
    # Bloquea campos que no deberían editarse manualmente (Auditoría)
    readonly_fields = ('fecha_ingreso',)

    # Organiza el formulario visualmente en bloques
    fieldsets = (
        ('Datos del Paciente', {
            'fields': ('paciente',)
        }),
        ('Signos Vitales', {
            'fields': ('presion_arterial', 'frecuencia_cardiaca', 'temperatura', 'saturacion_oxigeno')
        }),
        ('Evaluación Médica (Motor NLP)', {
            'fields': ('motivo_consulta', 'notas_medico', 'codigo_cie10_sugerido', 'procesado_por_ia')
        }),
        ('Resolución', {
            'fields': ('nivel_asignado',)
        }),
    )