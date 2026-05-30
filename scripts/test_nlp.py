import os
import sys
import django

# Configurar entorno Django
sys.path.append(os.path.join("C:\\software\\projects\\app-LIS", "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from consulta.services.nlp_service import extract_entities
from consulta.services.cie_lookup import search as cie_search
from consulta.services.med_lookup import search as med_search

def test_nlp_flow():
    text = "Paciente presenta fiebre alta, dolor de cabeza intenso y tos persistente. Se sospecha de infeccion respiratoria."
    print(f"Texto: {text}")
    
    # 1. Extraer entidades
    data = extract_entities(text)
    lemmas = data['lemmas']
    print(f"Lemas extraídos: {lemmas}")
    
    # 2. Buscar CIE-10
    query = " ".join(lemmas)
    cie_results = cie_search(query, limit=3)
    print("\nSugerencias CIE-10:")
    for res in cie_results:
        print(f"- {res['code']}: {res['description']}")
        
    # 3. Buscar Medicamentos
    med_results = med_search(query, limit=3)
    print("\nSugerencias Medicamentos:")
    for res in med_results:
        print(f"- {res['nombre']} ({res['presentacion']})")

if __name__ == "__main__":
    test_nlp_flow()
