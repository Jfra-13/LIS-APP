from django.contrib import admin

from .models import NotaMedica, Medicamento, Prescripcion


class PrescripcionInline(admin.TabularInline):
    model = Prescripcion
    extra = 1


@admin.register(NotaMedica)
class NotaMedicaAdmin(admin.ModelAdmin):
    list_display = ("id", "paciente", "triaje", "medico", "receta_id", "created_at")
    list_filter = ("medico", "created_at", "cie_accepted")
    search_fields = ("paciente__dni", "paciente__nombres", "contenido", "receta_id")
    readonly_fields = ("receta_id", "created_at", "updated_at")
    inlines = [PrescripcionInline]


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "presentacion", "concentracion")
    search_fields = ("nombre",)


@admin.register(Prescripcion)
class PrescripcionAdmin(admin.ModelAdmin):
    list_display = ("nota_medica", "medicamento", "dosis", "frecuencia")
    list_filter = ("medicamento",)

