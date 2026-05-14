from django.contrib import admin

from .models import NotaMedica


@admin.register(NotaMedica)
class NotaMedicaAdmin(admin.ModelAdmin):
    list_display = ("id", "paciente", "triaje", "medico", "created_at")
    list_filter = ("medico", "created_at")
    search_fields = ("paciente__dni", "paciente__nombres", "contenido")
    readonly_fields = ("created_at", "updated_at")

