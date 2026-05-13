from django.contrib import admin

from .models import Triaje


@admin.register(Triaje)
class TriajeAdmin(admin.ModelAdmin):
    list_display = (
        'paciente',
        'nivel_prioridad',
        'red_flag',
        'spo2',
        'frecuencia_cardiaca',
        'temperatura',
        'usuario_enfermeria',
        'created_at',
    )
    list_filter = ('nivel_prioridad', 'red_flag', 'created_at')
    search_fields = ('paciente__dni', 'paciente__nombres', 'paciente__apellidos')
    readonly_fields = (
        'id',
        'paciente',
        'spo2',
        'frecuencia_cardiaca',
        'temperatura',
        'red_flag',
        'nivel_prioridad',
        'observaciones',
        'usuario_enfermeria',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
