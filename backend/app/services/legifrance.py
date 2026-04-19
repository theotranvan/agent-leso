"""Intégration API Légifrance via PISTE (piste.gouv.fr) - OAuth2 client_credentials."""
import logging
import time
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
BASE_API = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
SEARCH_URL = f"{BASE_API}/search"
CONSULT_URL = f"{BASE_API}/consult"


class LegifranceClient:
    """Client Légifrance avec gestion automatique du token OAuth2."""

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    async def _get_token(self) -> str:
        """Récupère un token OAuth2 (cache 55 min)."""
        now = time.time()
        if self._token and now < self._token_expires_at - 60:
            return self._token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.LEGIFRANCE_CLIENT_ID,
                    "client_secret": settings.LEGIFRANCE_CLIENT_SECRET,
                    "scope": "openid",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            data = response.json()

        self._token = data["access_token"]
        self._token_expires_at = now + data.get("expires_in", 3600)
        return self._token

    async def search_recent(
        self,
        keywords: list[str],
        days_back: int = 7,
        fonds: list[str] | None = None,
    ) -> list[dict]:
        """Recherche les textes récents contenant l'un des mots-clés.

        fonds: ['LODA_DATE', 'JORF', 'CODE_DATE', ...]. Par défaut on interroge LODA + JORF.
        """
        from datetime import datetime, timedelta

        fonds = fonds or ["LODA_DATE", "JORF"]
        token = await self._get_token()
        end = datetime.utcnow()
        start = end - timedelta(days=days_back)

        query = " OR ".join(f'"{kw}"' for kw in keywords)

        payload = {
            "recherche": {
                "champs": [{
                    "typeChamp": "ALL",
                    "criteres": [{
                        "typeRecherche": "UN_DES_MOTS",
                        "valeur": query,
                        "operateur": "ET",
                    }],
                    "operateur": "ET",
                }],
                "filtres": [{
                    "facette": "DATE_VERSION",
                    "dates": {
                        "start": start.strftime("%Y-%m-%d"),
                        "end": end.strftime("%Y-%m-%d"),
                    },
                }],
                "pageNumber": 1,
                "pageSize": 20,
                "sort": "DATE_DESC",
                "operateur": "ET",
                "typePagination": "DEFAUT",
            },
            "fond": fonds[0] if len(fonds) == 1 else "ALL",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    SEARCH_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Légifrance search failed: {e.response.status_code} {e.response.text[:500]}")
                return []
            except Exception as e:
                logger.error(f"Légifrance search erreur: {e}")
                return []

        results = []
        for item in data.get("results", [])[:20]:
            titles = item.get("titles", [])
            title = titles[0].get("title", "Sans titre") if titles else "Sans titre"
            results.append({
                "title": title,
                "url": f"https://www.legifrance.gouv.fr/loda/id/{item.get('id', '')}" if item.get("id") else None,
                "nature": item.get("nature"),
                "date": item.get("date"),
                "id": item.get("id"),
                "origin": item.get("origin"),
                "text_id": item.get("titles", [{}])[0].get("cid") if titles else None,
            })
        return results

    async def consult_article(self, article_id: str) -> dict[str, Any]:
        """Récupère le contenu d'un article ou d'un texte."""
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{CONSULT_URL}/getArticle",
                    json={"id": article_id},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Erreur consult article: {e}")
                return {}


# Mots-clés surveillés pour la veille BET
VEILLE_KEYWORDS = {
    "thermique": ["RE2020", "réglementation thermique", "performance énergétique bâtiment", "DPE"],
    "structure": ["Eurocode", "NF EN 1992", "NF EN 1993", "NF EN 1995", "DTU"],
    "acoustique": ["acoustique bâtiment", "NRA", "NF S31"],
    "electricite": ["NF C 15-100", "NF C 14-100", "installation électrique"],
    "incendie": ["sécurité incendie", "ERP", "IGH", "arrêté incendie"],
    "accessibilite": ["accessibilité PMR", "handicapé", "arrêté accessibilité"],
    "general": ["arrêté construction", "décret construction", "bâtiment neuf"],
}


async def daily_veille_all_domains() -> dict[str, list[dict]]:
    """Lance la veille sur tous les domaines. Retourne {domaine: [alertes]}."""
    client = LegifranceClient()
    all_alerts: dict[str, list[dict]] = {}
    for domain, keywords in VEILLE_KEYWORDS.items():
        try:
            results = await client.search_recent(keywords, days_back=2)
            all_alerts[domain] = results
        except Exception as e:
            logger.error(f"Veille domaine {domain} échouée: {e}")
            all_alerts[domain] = []
    return all_alerts
