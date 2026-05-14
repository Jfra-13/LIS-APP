from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "cie10.json"


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    with DATA_FILE.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("El catálogo CIE-10 debe ser una lista JSON.")
    return data


def _score_entry(entry: dict[str, Any], query: str, tokens: list[str]) -> int:
    score = 0
    code = normalize_text(entry.get("code"))
    short_description = normalize_text(entry.get("short_description"))
    description = normalize_text(entry.get("description"))
    group = normalize_text(entry.get("group"))
    keywords = [normalize_text(item) for item in entry.get("keywords", [])]
    phrases = [normalize_text(item) for item in entry.get("phrases", [])]
    synonyms = [normalize_text(item) for item in entry.get("synonyms", [])]
    weighted_keywords = {
        normalize_text(key): int(value)
        for key, value in (entry.get("keywords_weight") or {}).items()
    }

    if query == code:
        score += 1000
    if query == short_description:
        score += 400
    if query in short_description:
        score += 250
    if query in description:
        score += 120
    if query in group:
        score += 50

    for phrase in phrases:
        if query == phrase:
            score += 350
        elif query in phrase or phrase in query:
            score += 180

    for synonym in synonyms:
        if query == synonym:
            score += 260
        elif query in synonym or synonym in query:
            score += 140

    for keyword in keywords:
        if query == keyword:
            score += 220
        elif query in keyword or keyword in query:
            score += 110

    for token in tokens:
        if token and token in short_description:
            score += 45
        if token and token in description:
            score += 18
        if token and token in group:
            score += 10
        if token in keywords:
            score += 60
        if token in phrases:
            score += 70
        if token in synonyms:
            score += 65
        score += int(weighted_keywords.get(token, 0)) * 10

    if entry.get("emergency_flag"):
        score += 20

    severity = entry.get("severity")
    if isinstance(severity, int):
        score += max(0, 5 - severity) * 5

    return score


def search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    tokens = [token for token in normalized_query.split() if token]
    matches: list[tuple[int, dict[str, Any]]] = []

    for entry in load_catalog():
        score = _score_entry(entry, normalized_query, tokens)
        if score > 0:
            matches.append((score, entry))

    matches.sort(
        key=lambda item: (
            item[0],
            int(bool(item[1].get("emergency_flag"))),
            -(item[1].get("severity") or 99),
            normalize_text(item[1].get("code")),
        ),
        reverse=True,
    )
    return [entry for _, entry in matches[:limit]]

