from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .cie_lookup import normalize_text

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "medicamentos.json"


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("El catálogo de medicamentos debe ser una lista JSON.")
    return data


def _score_entry(entry: dict[str, Any], query: str, tokens: list[str]) -> int:
    score = 0
    nombre = normalize_text(entry.get("nombre"))
    presentacion = normalize_text(entry.get("presentacion"))
    concentracion = normalize_text(entry.get("concentracion"))
    keywords = [normalize_text(k) for k in entry.get("keywords", [])]

    # Búsqueda exacta en nombre
    if query == nombre:
        score += 1000
    # Búsqueda parcial en nombre
    elif query in nombre:
        score += 500

    # Búsqueda en keywords
    for keyword in keywords:
        if query == keyword:
            score += 400
        elif query in keyword or keyword in query:
            score += 150

    # Búsqueda por tokens
    for token in tokens:
        if token == nombre:
            score += 300
        elif token in nombre:
            score += 100
        
        if token in keywords:
            score += 80
            
        if token in presentacion:
            score += 50

        
        if token in concentracion:
            score += 50
    return score


def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    tokens = [token for token in normalized_query.split() if token]
    matches: list[tuple[int, dict[str, Any]]] = []

    for entry in load_catalog():
        score = _score_entry(entry, normalized_query, tokens)
        if score > 0:
            matches.append((score, entry))

    matches.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in matches[:limit]]
