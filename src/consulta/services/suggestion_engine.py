from __future__ import annotations

import logging
from typing import Any

from .cie_lookup import search as cie_search

logger = logging.getLogger(__name__)


def _lemmatize(text: str) -> list[str]:
    """Normaliza el texto clínico a lemas usando spaCy.

    spaCy actúa SOLO como normalizador lingüístico: quita stopwords y extrae
    lemas. No clasifica ni decide (no es una caja negra de ML). Si el modelo
    no está disponible, degrada a una lista vacía y el motor cae al texto
    crudo, manteniendo el sistema funcional.
    """
    try:
        from .nlp_service import extract_entities

        return extract_entities(text).get("lemmas", [])
    except Exception:
        logger.warning(
            "spaCy no disponible; el motor CIE-10 usará el texto crudo",
            exc_info=True,
        )
        return []


def suggest_cie(text: str, limit: int = 5) -> list[dict[str, Any]]:
    """Motor híbrido de sugerencia CIE-10.

    Flujo: texto clínico -> spaCy lematiza/limpia -> lemas -> cie_lookup
    cruza los lemas contra el catálogo JSON determinístico. El matching es
    auditable y sin caja negra. Si spaCy no está disponible, usa el texto
    crudo como query.
    """
    text = (text or "").strip()
    if not text:
        return []

    lemmas = _lemmatize(text)
    query = " ".join(lemmas) if lemmas else text
    return cie_search(query, limit=limit)
