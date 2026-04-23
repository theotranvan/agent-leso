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


async def sparql_query(query: str, timeout: float = 30.0) -> dict[str, Any]:
    """Exécute une requête SPARQL sur l'endpoint Fedlex.

    Endpoint officiel : https://fedlex.data.admin.ch/sparqlendpoint
    Format : application/sparql-results+json
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                FEDLEX_SPARQL,
                data={"query": query},
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "BET-Agent/3.0 (contact: team@bet-agent.ch)",
                },
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"SPARQL HTTP error {e.response.status_code}: {e.response.text[:500]}")
            return {}
        except Exception as e:
            logger.error(f"SPARQL query error: {e}")
            return {}


async def sparql_recent_acts(days_back: int = 7, limit: int = 50) -> list[dict]:
    """Recherche des actes législatifs fédéraux récents via SPARQL.

    Retourne les actes (loi, ordonnance) publiés dans les N derniers jours.
    Schéma Fedlex : utilise `jolux:dateApplicability` pour l'entrée en vigueur.
    """
    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    query = f"""
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?uri ?title ?date ?type WHERE {{
  ?uri a jolux:ConsolidationAbstract .
  ?uri jolux:dateApplicability ?date .
  ?uri jolux:title ?title .
  OPTIONAL {{ ?uri jolux:typeDocument ?type . }}
  FILTER (?date >= "{from_date}"^^<http://www.w3.org/2001/XMLSchema#date>)
  FILTER (LANG(?title) = "fr")
}}
ORDER BY DESC(?date)
LIMIT {limit}
"""

    data = await sparql_query(query)
    if not data:
        return []

    bindings = data.get("results", {}).get("bindings", []) or []
    results: list[dict] = []
    for b in bindings:
        try:
            uri = b.get("uri", {}).get("value")
            title = b.get("title", {}).get("value", "").strip()
            date = b.get("date", {}).get("value", "")
            doc_type = b.get("type", {}).get("value", "") if "type" in b else ""
            if uri and title:
                results.append({
                    "source_url": uri,
                    "title": title,
                    "detected_at": datetime.utcnow().isoformat(),
                    "publication_date": date,
                    "document_type": doc_type.split("/")[-1] if doc_type else "acte",
                    "method": "sparql",
                })
        except Exception as e:
            logger.debug(f"Parse binding Fedlex échec : {e}")

    return results


async def sparql_search_keyword(keyword: str, days_back: int = 30, limit: int = 20) -> list[dict]:
    """Recherche par mot-clé dans les actes Fedlex récents."""
    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    keyword_safe = keyword.replace('"', '').replace('\\', '')

    query = f"""
PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>

SELECT DISTINCT ?uri ?title ?date WHERE {{
  ?uri jolux:title ?title .
  ?uri jolux:dateApplicability ?date .
  FILTER (CONTAINS(LCASE(?title), LCASE("{keyword_safe}")))
  FILTER (?date >= "{from_date}"^^<http://www.w3.org/2001/XMLSchema#date>)
  FILTER (LANG(?title) = "fr")
}}
ORDER BY DESC(?date)
LIMIT {limit}
"""

    data = await sparql_query(query)
    if not data:
        return []

    bindings = data.get("results", {}).get("bindings", []) or []
    results: list[dict] = []
    for b in bindings:
        try:
            results.append({
                "source_url": b["uri"]["value"],
                "title": b["title"]["value"].strip(),
                "publication_date": b["date"]["value"],
                "keyword_matched": keyword,
                "detected_at": datetime.utcnow().isoformat(),
                "method": "sparql",
            })
        except (KeyError, TypeError):
            continue

    return results


async def daily_fedlex_veille() -> list[dict]:
    """Run quotidien de veille Fedlex sur tous les domaines BET.

    Stratégie à 2 niveaux :
      1. SPARQL officiel (prioritaire) : requête par mot-clé sur actes récents
      2. Fallback scraping HTML si SPARQL échoue (réseau/endpoint down)
    """
    all_results: list[dict] = []

    # Niveau 1 : SPARQL officiel
    sparql_ok = False
    for domain, keywords in FEDLEX_KEYWORDS.items():
        for keyword in keywords[:3]:  # top 3 keywords par domaine
            try:
                items = await sparql_search_keyword(keyword, days_back=2, limit=10)
                for r in items:
                    r["domain"] = domain
                all_results.extend(items)
                if items:
                    sparql_ok = True
            except Exception as e:
                logger.debug(f"SPARQL keyword '{keyword}' échec : {e}")

    # Complément : actes très récents (sans filtre mot-clé)
    if sparql_ok:
        try:
            recent = await sparql_recent_acts(days_back=2, limit=20)
            for r in recent:
                r["domain"] = "general"
            all_results.extend(recent)
        except Exception as e:
            logger.warning(f"SPARQL recent_acts échec : {e}")

    # Niveau 2 : fallback HTML scraping si SPARQL a tout raté
    if not sparql_ok:
        logger.warning("SPARQL Fedlex indisponible, fallback HTML scraping")
        for domain, keywords in FEDLEX_KEYWORDS.items():
            try:
                domain_results = await search_recent_fedlex(keywords, days_back=2)
                for r in domain_results:
                    r["domain"] = domain
                    r.setdefault("method", "html_scraping")
                all_results.extend(domain_results)
            except Exception as e:
                logger.error(f"HTML fallback domain '{domain}' échec : {e}")

    # Déduplication par URL
    seen: set[str] = set()
    unique: list[dict] = []
    for r in all_results:
        url = r.get("source_url")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)

    logger.info(f"Veille Fedlex : {len(unique)} actes uniques ({'SPARQL' if sparql_ok else 'HTML'})")
    return unique
