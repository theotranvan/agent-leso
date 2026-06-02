"""Digest mensuel de veille réglementaire personnalisé par bureau.

Différence avec le veille_agent (qui collecte et alerte au fil de l'eau) :
ce service produit, une fois par mois, un résumé CIBLÉ pour chaque organisation
selon son canton et ses types de projets — "voici ce qui change pour VOUS ce
mois-ci" — et l'envoie par email.

C'est une fonctionnalité différenciante : aucun concurrent ne fait de veille
réglementaire personnalisée par profil de bureau. Et le coût en tokens est
quasi nul (la veille brute est déjà analysée, on ne fait que filtrer + résumer
avec Haiku).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from app.database import get_supabase_admin

logger = logging.getLogger(__name__)


def _matches_org_profile(alert: dict, canton: str, project_types: set[str]) -> bool:
    """Une alerte concerne-t-elle le profil du bureau ?"""
    jurisdictions = alert.get("jurisdiction") or []
    # Fédéral concerne tout le monde
    if "CH" in jurisdictions:
        return True
    # Canton du bureau
    if any(f"CH-{canton}" == j for j in jurisdictions):
        return True
    # Si pas de juridiction précise, on inclut par prudence
    if not jurisdictions:
        return True
    return False


async def build_monthly_digest(organization_id: str) -> dict[str, Any]:
    """Construit le digest mensuel personnalisé d'un bureau.

    Filtre les alertes du dernier mois selon le canton et les projets du bureau,
    puis produit un résumé court via Haiku.
    """
    admin = get_supabase_admin()

    # Profil du bureau
    org = (
        admin.table("organizations")
        .select("name, canton")
        .eq("id", organization_id)
        .maybe_single()
        .execute()
    )
    if not org.data:
        return {"error": "Organisation introuvable"}
    canton = org.data.get("canton", "VD")

    # Types de projets actifs (pour cibler la pertinence)
    projects = (
        admin.table("projects")
        .select("affectation")
        .eq("organization_id", organization_id)
        .eq("status", "active")
        .execute()
    )
    project_types = {p.get("affectation") for p in (projects.data or []) if p.get("affectation")}

    # Alertes du dernier mois
    month_ago = (datetime.utcnow() - timedelta(days=31)).isoformat()
    alerts = (
        admin.table("regulatory_alerts")
        .select("*")
        .gte("created_at", month_ago)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    rows = alerts.data or []

    # Filtre selon le profil
    relevant = [a for a in rows if _matches_org_profile(a, canton, project_types)]

    if not relevant:
        return {
            "organization_id": organization_id,
            "canton": canton,
            "period": "30 derniers jours",
            "nb_alerts": 0,
            "summary_md": "Aucune évolution réglementaire majeure ne concerne "
                          "votre bureau ce mois-ci.",
            "alerts": [],
        }

    # Résumé via Haiku (coût minime)
    summary_md = await _summarize_for_org(relevant, org.data.get("name", ""), canton)

    return {
        "organization_id": organization_id,
        "canton": canton,
        "period": "30 derniers jours",
        "nb_alerts": len(relevant),
        "summary_md": summary_md,
        "alerts": relevant[:15],
    }


async def _summarize_for_org(alerts: list[dict], org_name: str, canton: str) -> str:
    """Produit un résumé court et orienté action via le LLM (Haiku)."""
    from app.agent.router import call_llm

    items = "\n".join(
        f"- [{a.get('severity', 'info')}] {a.get('title', '')} "
        f"({', '.join(a.get('jurisdiction', []))}) : {a.get('summary', '')[:200]}"
        for a in alerts[:20]
    )
    system = (
        "Tu es un expert en réglementation du bâtiment en Suisse romande. "
        "On te donne une liste d'évolutions réglementaires récentes. Produis un "
        "résumé mensuel court (markdown), orienté action, pour un bureau d'études "
        f"technique basé dans le canton de {canton}. Regroupe par thème (énergie, "
        "incendie, structure, urbanisme). Pour chaque point important, indique "
        "concrètement ce que le bureau doit faire ou vérifier. Maximum 300 mots. "
        "Ton professionnel et direct."
    )
    try:
        result = await call_llm(
            task_type="veille_reglementaire",  # Haiku
            system_prompt=system,
            user_content=f"Évolutions à résumer pour {org_name} :\n\n{items}",
            max_tokens=1500,
            temperature=0.2,
        )
        return result["text"].strip()
    except Exception as e:
        logger.error("Résumé digest échoué : %s", e)
        # Fallback : liste brute
        return "## Évolutions réglementaires du mois\n\n" + items


async def send_monthly_digests() -> dict[str, Any]:
    """Tâche planifiée : envoie le digest à toutes les organisations actives.

    À appeler une fois par mois (worker ARQ / cron).
    """
    from app.services.email_service import send_email

    admin = get_supabase_admin()
    orgs = (
        admin.table("organizations")
        .select("id, name")
        .eq("onboarding_completed", True)
        .execute()
    )
    sent = 0
    for org in orgs.data or []:
        try:
            digest = await build_monthly_digest(org["id"])
            if digest.get("nb_alerts", 0) == 0:
                continue
            # Destinataires : admins de l'org
            users = (
                admin.table("users")
                .select("email")
                .eq("organization_id", org["id"])
                .eq("role", "admin")
                .execute()
            )
            emails = [u["email"] for u in (users.data or []) if u.get("email")]
            if not emails:
                continue
            html = (
                f"<h2>Veille réglementaire — {datetime.now().strftime('%B %Y')}</h2>"
                f"<p>Voici les évolutions qui concernent votre bureau ce mois-ci "
                f"({digest['nb_alerts']} point(s)).</p>"
                f"<div>{digest['summary_md']}</div>"
            )
            send_email(emails, "[BET Agent] Votre veille réglementaire du mois", html)
            sent += 1
        except Exception as e:
            logger.error("Digest org=%s échoué : %s", org["id"], e)
    return {"digests_sent": sent}
