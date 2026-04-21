import uuid
from django.db import models


class Paciente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dni = models.CharField(max_length=15, unique=True)
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    fecha_nacimiento = models.DateField()
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.apellidos}, {self.nombre} ({self.dni})"


class RegistroTriage(models.Model):
    NIVELES_PRIORIDAD = [
        ('1', 'Nivel 1 - Resucitación (Inmediata)'),
        ('2', 'Nivel 2 - Emergencia (10-15 min)'),
        ('3', 'Nivel 3 - Urgencia (60 min)'),
        ('4', 'Nivel 4 - Urgencia Menor (2 hrs)'),
        ('5', 'Nivel 5 - Sin Urgencia (4 hrs)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='triages')

    # Signos Vitales
    presion_arterial = models.CharField(max_length=7, help_text="Ej: 120/80")
    frecuencia_cardiaca = models.IntegerField(help_text="LPM")
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, help_text="°C")
    saturacion_oxigeno = models.IntegerField(help_text="%")

    # Evaluación Clínica
    motivo_consulta = models.TextField()
    notas_medico = models.TextField(blank=True, null=True, help_text="Aquí el motor NLP extraerá el código CIE-10")

    # Resultados y Trazabilidad
    nivel_asignado = models.CharField(max_length=1, choices=NIVELES_PRIORIDAD, default='3')
    codigo_cie10_sugerido = models.CharField(max_length=10, blank=True, null=True)

    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    procesado_por_ia = models.BooleanField(default=False)

    def __str__(self):
        return f"Triage {self.nivel_asignado} - {self.paciente.apellidos} - {self.fecha_ingreso.strftime('%Y-%m-%d')}"