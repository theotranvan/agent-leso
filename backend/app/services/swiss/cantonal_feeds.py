"""Veille cantonale romande - scrapers ciblés.

Chaque canton expose sa législation sur un portail différent. On utilise une approche
RSS / flux officiels quand ils existent, sinon scraping HTML.

Sources par canton :
- GE : ge.ch/legislation (cherche Feuille d'Avis Officielle)
- VD : prestations.vd.ch/pub/blv-publication (BLV)
- NE : rsn.ne.ch
- FR : bdlf.fr.ch
- VS : lex.vs.ch
- JU : rsju.jura.ch
"""
import logging
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


CANTONAL_SOURCES = {
    "GE": {
        "name": "Genève - Législation cantonale",
        "search_url": "https://www.ge.ch/legislation/rsg/",
        "foa_url": "https://www.ge.ch/document/feuille-avis-officielle",
    },
    "VD": {
        "name": "Vaud - Base législative",
        "search_url": "https://prestations.vd.ch/pub/blv-publication/",
    },
    "NE": {
        "name": "Neuchâtel - Recueil systématique",
        "search_url": "https://rsn.ne.ch/",
    },
    "FR": {
        "name": "Fribourg - Base de données législative",
        "search_url": "https://bdlf.fr.ch/",
    },
    "VS": {
        "name": "Valais - Systématique",
        "search_url": "https://lex.vs.ch/",
    },
    "JU": {
        "name": "Jura - Recueil systématique",
        "search_url": "https://rsju.jura.ch/",
    },
}


async def fetch_canton_updates(canton: str, keywords: list[str]) -> list[dict]:
    """Récupère les récentes publications cantonales correspondant aux mots-clés.

    Implémentation défensive : si le canton n'a pas d'API ouverte, retourne une liste vide
    plutôt que d'échouer.
    """
    source = CANTONAL_SOURCES.get(canton)
    if not source:
        return []

    results: list[dict] = []
    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "BET-Agent/2.0 (legal research)"}
    ) as client:
        try:
            # Approche générique : on tente une requête de recherche avec chaque mot-clé
            for keyword in keywords[:3]:
                try:
                    response = await client.get(
                        source["search_url"],
                        params={"q": keyword} if "search_url" in source else {},
                        follow_redirects=True,
                    )
                    if response.status_code == 200:
                        # Extraction minimale. Un parseur plus fin est nécessaire par canton en V3.
                        import re
                        links = re.findall(
                            r'href="([^"]+)"[^>]*>([^<]{15,200})</a>',
                            response.text,
                        )
                        for href, title in links[:5]:
                            if any(kw in title.lower() for kw in ["énergie", "construction", "bâtiment", "thermique", "incendie"]):
                                full_url = href if href.startswith("http") else source["search_url"] + href
                                results.append({
                                    "source_url": full_url,
                                    "title": title.strip()[:300],
                                    "canton": canton,
                                    "keyword_matched": keyword,
                                    "detected_at": datetime.utcnow().isoformat(),
                                })
                except Exception as e:
                    logger.debug(f"Canton {canton} keyword '{keyword}' error: {e}")
        except Exception as e:
            logger.warning(f"Canton {canton} scraping failed: {e}")

    return results[:10]


KEYWORDS_CANTONAUX_BET = [
    "énergie bâtiment",
    "CECB",
    "isolation thermique",
    "IDC",
    "construction autorisation",
    "permis construire",
    "rénovation énergétique",
    "subvention bâtiment",
    "incendie directive",
]


async def daily_cantonal_veille(cantons: list[str] | None = None) -> dict[str, list[dict]]:
    """Run quotidien sur les cantons romands."""
    cantons = cantons or ["GE", "VD", "NE", "FR", "VS", "JU"]
    results: dict[str, list[dict]] = {}
    for c in cantons:
        try:
            items = await fetch_canton_updates(c, KEYWORDS_CANTONAUX_BET)
            results[c] = items
        except Exception as e:
            logger.error(f"Veille canton {c} échouée: {e}")
            results[c] = []
    return results
