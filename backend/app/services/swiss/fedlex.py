"""Connecteur Fedlex - Recueil systématique du droit fédéral suisse.

Fedlex publie un point d'accès SPARQL ouvert (https://fedlex.data.admin.ch/).
On utilise ici l'approche pragmatique : interrogation du moteur de recherche
et des flux RSS/Atom disponibles publiquement.

Note : ce connecteur privilégie la résilience et l'absence de dépendance
à une API propriétaire. Tout changement côté Fedlex nécessitera une adaptation.
"""
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Endpoints publics
FEDLEX_SEARCH_BASE = "https://www.fedlex.admin.ch/eli/ofs/fr"
FEDLEX_SPARQL = "https://fedlex.data.admin.ch/sparqlendpoint"

# Mots-clés surveillés (domaines BET)
FEDLEX_KEYWORDS = {
    "thermique": [
        "énergie bâtiment", "efficacité énergétique", "LEne", "CECB",
        "rendement énergétique", "chauffage rénovation",
    ],
    "incendie": [
        "protection incendie", "AEAI", "prescription incendie",
    ],
    "structure": [
        "ouvrage construction", "sécurité structurelle",
    ],
    "accessibilite": [
        "handicapé construction", "LHand bâtiment", "accessibilité LCAP",
    ],
    "general": [
        "ordonnance construction", "loi bâtiment", "aménagement territoire",
    ],
}


async def search_recent_fedlex(keywords: list[str], days_back: int = 7) -> list[dict]:
    """Recherche des textes récents dans Fedlex.

    Cette implémentation utilise le flux RSS des mises à jour Fedlex.
    Si Fedlex change de format, adapter ici.
    """
    since = datetime.utcnow() - timedelta(days=days_back)
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "BET-Agent/2.0"}) as client:
        for keyword in keywords[:5]:  # limite 5 pour éviter flood
            try:
                # Fedlex ne propose pas d'API REST simple ; on fait une recherche HTML minimale
                # Pour une intégration propre, passer au SPARQL endpoint
                response = await client.get(
                    "https://www.fedlex.admin.ch/fr/search",
                    params={"q": keyword, "scope": "cc", "sort": "date_desc"},
                    follow_redirects=True,
                )
                if response.status_code != 200:
                    logger.warning(f"Fedlex search status {response.status_code} pour '{keyword}'")
                    continue

                # Extraction minimale (regex sur la page HTML - à remplacer par SPARQL en V3)
                import re
                html = response.text
                # Pattern indicatif - à ajuster selon structure réelle de Fedlex
                matches = re.findall(
                    r'href="(/eli/cc/[^"]+)"[^>]*>([^<]{10,200})</a>',
                    html,
                )
                for url_path, title in matches[:10]:
                    full_url = f"https://www.fedlex.admin.ch{url_path}"
                    if any(r["source_url"] == full_url for r in results):
                        continue
                    results.append({
                        "source_url": full_url,
                        "title": title.strip(),
                        "keyword_matched": keyword,
                        "detected_at": datetime.utcnow().isoformat(),
                    })
            except Exception as e:
                logger.error(f"Fedlex search '{keyword}' error: {e}")

    return results[:30]


async def sparql_query(query: str) -> dict[str, Any]:
    """Exécute une requête SPARQL sur l'endpoint Fedlex.

    Utile pour des recherches structurées précises (en V3).
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                FEDLEX_SPARQL,
                data={"query": query, "format": "application/sparql-results+json"},
                headers={"Accept": "application/sparql-results+json"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"SPARQL query error: {e}")
            return {}


async def daily_fedlex_veille() -> list[dict]:
    """Run quotidien de veille Fedlex sur tous les domaines BET."""
    all_results: list[dict] = []
    for domain, keywords in FEDLEX_KEYWORDS.items():
        domain_results = await search_recent_fedlex(keywords, days_back=2)
        for r in domain_results:
            r["domain"] = domain
        all_results.extend(domain_results)

    # Déduplication par URL
    seen = set()
    unique = []
    for r in all_results:
        if r["source_url"] not in seen:
            seen.add(r["source_url"])
            unique.append(r)
    return unique
