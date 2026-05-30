import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
# Asegúrate de que tu modelo se llame 'Medicamento' y ajusta la importación si es necesario.
from consulta.models import Medicamento 

class Command(BaseCommand):
    help = 'Carga el catálogo de medicamentos desde medicamentos.json'

    def handle(self, *args, **kwargs):
        # Construimos la ruta absoluta hacia tu archivo JSON
        ruta_archivo = os.path.join(settings.BASE_DIR, 'consulta', 'data', 'medicamentos.json')
        
        if not os.path.exists(ruta_archivo):
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo en: {ruta_archivo}'))
            return

        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            medicamentos_data = json.load(archivo)

        # Limpiar la tabla antes de cargar para evitar duplicados si lo corres varias veces
        Medicamento.objects.all().delete()
        self.stdout.write(self.style.WARNING('Tabla de medicamentos limpiada.'))

        for item in medicamentos_data:
            Medicamento.objects.create(
                nombre=item['nombre'],
                presentacion=item['presentacion'],
                concentracion=item['concentracion'],
            )
            
        self.stdout.write(self.style.SUCCESS(f'¡Se han cargado {len(medicamentos_data)} medicamentos exitosamente!'))