import spacy
from typing import List, Dict, Any
from functools import lru_cache


@lru_cache(maxsize=1)
def load_nlp():
    """Carga el modelo spaCy en español.

    El modelo se instala en tiempo de build (ver Dockerfile.worker). Si no
    está disponible, se propaga ``OSError`` para que la capa superior degrade
    a texto crudo. No se descarga en runtime: bajar el modelo dentro del
    worker añade latencia, dependencia de red y cuelga las pruebas.
    """
    return spacy.load("es_core_news_sm")

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extrae entidades relevantes (síntomas, partes del cuerpo, etc.) del texto clínico.
    """
    if not text:
        return {"entities": [], "lemmas": []}
    
    nlp = load_nlp()
    doc = nlp(text)
    
    entities = []
    # Extraemos sustantivos y adjetivos que suelen representar síntomas o estados
    relevant_tokens = []
    
    for token in doc:
        # Filtrar stop words y puntuación
        if not token.is_stop and not token.is_punct:
            if token.pos_ in ["NOUN", "ADJ", "VERB"]:
                relevant_tokens.append(token.lemma_.lower())
    
    # NER
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_
        })
        
    return {
        "entities": entities,
        "lemmas": list(set(relevant_tokens))
    }
