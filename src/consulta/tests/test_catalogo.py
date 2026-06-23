"""P5 — integridad del catálogo de medicamentos y el mapa CIE→meds."""
import json
from pathlib import Path

import pytest
from django.core.management import call_command

from consulta.models import Medicamento

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _cie_med_map() -> dict:
    with (DATA_DIR / "cie_med_map.json").open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.django_db
def test_cargar_medicamentos_puebla_catalogo():
    call_command("cargar_medicamentos")
    with (DATA_DIR / "medicamentos.json").open(encoding="utf-8") as fh:
        esperado = len(json.load(fh))
    assert Medicamento.objects.count() == esperado
    assert esperado >= 20  # catálogo ampliado con variedad real


@pytest.mark.django_db
def test_todo_nombre_del_mapa_existe_en_db():
    """Tras cargar el catálogo, cada nombre del mapa CIE→meds resuelve en la BD
    con la misma lógica `icontains` que usa `med_suggest_by_cie`."""
    call_command("cargar_medicamentos")

    sin_resolver = []
    for cie, nombres in _cie_med_map().items():
        for nombre in nombres:
            if not Medicamento.objects.filter(nombre__icontains=nombre).exists():
                sin_resolver.append((cie, nombre))

    assert not sin_resolver, f"Nombres del mapa sin medicamento en BD: {sin_resolver}"


@pytest.mark.django_db
def test_sales_de_rehidratacion_oral_presente():
    call_command("cargar_medicamentos")
    assert Medicamento.objects.filter(nombre__icontains="Rehidratacion Oral").exists()
