import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from consulta.models import Medicamento


class Command(BaseCommand):
    help = "Carga/actualiza el catálogo de medicamentos desde medicamentos.json"

    def handle(self, *args, **kwargs):
        ruta_archivo = os.path.join(
            settings.BASE_DIR, "consulta", "data", "medicamentos.json"
        )

        if not os.path.exists(ruta_archivo):
            self.stdout.write(
                self.style.ERROR(f"No se encontró el archivo en: {ruta_archivo}")
            )
            return

        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            medicamentos_data = json.load(archivo)

        # Upsert en vez de borrar: `Prescripcion.medicamento` es on_delete=PROTECT,
        # así que un delete-all rompe (ProtectedError) en cuanto existe una receta.
        # update_or_create por (nombre, presentacion) mantiene estables los pks
        # UUID que las recetas ya referencian y agrega/actualiza el resto.
        creados, actualizados = 0, 0
        for item in medicamentos_data:
            _, created = Medicamento.objects.update_or_create(
                nombre=item["nombre"],
                presentacion=item["presentacion"],
                defaults={"concentracion": item["concentracion"]},
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo cargado: {creados} nuevos, {actualizados} actualizados "
                f"({len(medicamentos_data)} en el archivo)."
            )
        )
