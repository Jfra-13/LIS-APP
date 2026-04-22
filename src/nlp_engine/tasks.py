import os
import json
import spacy
from spacy.matcher import PhraseMatcher
from celery import shared_task
from django.conf import settings
from triage.models import RegistroTriage

# 1. Cargamos el modelo en español de spaCy (fuera de la función para mayor velocidad)
nlp = spacy.load("es_core_news_sm")


@shared_task
def procesar_diagnostico_cie10(triage_id, texto_medico):
    print(f"[{triage_id}] Iniciando escaneo NLP real para: '{texto_medico}'")

    # 2. Leer tu catálogo JSON
    ruta_json = os.path.join(settings.BASE_DIR, 'nlp_engine', 'cie10_data.json')
    with open(ruta_json, 'r', encoding='utf-8') as f:
        catalogo = json.load(f)

    # 3. Configurar el "Buscador Inteligente" de spaCy
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")  # LOWER ignora mayúsculas

    # Le enseñamos a spaCy los códigos y sus sinónimos
    for enfermedad in catalogo:
        codigo = enfermedad["codigo"]
        # Convertimos los términos clave a un formato que spaCy entienda
        patrones = [nlp.make_doc(termino) for termino in enfermedad["terminos_clave"]]
        matcher.add(codigo, patrones)

    # 4. Analizar la nota del médico
    doc = nlp(texto_medico)
    coincidencias = matcher(doc)

    # Código por defecto si la IA no entiende nada (R69 = Causas desconocidas)
    resultado_sugerido = "R69"

    if coincidencias:
        # Si encuentra algo, tomamos el primer Match
        match_id, start, end = coincidencias[0]
        resultado_sugerido = nlp.vocab.strings[match_id]
        palabra_detectada = doc[start:end].text
        print(f"[{triage_id}] ¡Match NLP Exitoso!: Detectó '{palabra_detectada}' -> Asigna código {resultado_sugerido}")
    else:
        print(f"[{triage_id}] La IA no encontró coincidencias en el diccionario.")

    # 5. Guardar el resultado real en la Base de Datos
    triage = RegistroTriage.objects.get(id=triage_id)
    triage.codigo_cie10_sugerido = resultado_sugerido
    triage.procesado_por_ia = True
    triage.save()

    return resultado_sugerido