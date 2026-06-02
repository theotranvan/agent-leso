"""Mode bureau certifié BET Agent.

Un bureau qui produit et valide ses dossiers avec BET Agent peut afficher un
label "Bureau certifié BET Agent" sur son site et ses documents. Ça crée :
- de la fidélisation (le bureau valorise son usage de l'outil)
- de la publicité gratuite (chaque badge pointe vers BET Agent)
- de la confiance côté maîtres d'ouvrage (dossiers produits avec un outil reconnu)

La certification est attribuée selon des critères objectifs (nombre de dossiers
produits et validés, taux de validation). Une page publique permet de vérifier
l'authenticité d'un badge.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any

from app.database import get_supabase_admin

logger = logging.getLogger(__name__)


# Critères d'obtention de la certification
CERT_MIN_APPROVED_DOCS = 10        # documents validés minimum
CERT_MIN_APPROVAL_RATE = 70        # taux d'approbation minimum (%)

# Niveaux de certification selon le volume
CERT_LEVELS = [
    (100, "Or", "Bureau certifié BET Agent — Or"),
    (40, "Argent", "Bureau certifié BET Agent — Argent"),
    (10, "Bronze", "Bureau certifié BET Agent — Bronze"),
]


def compute_certification(organization_id: str) -> dict[str, Any]:
    """Évalue l'éligibilité et le niveau de certification d'un bureau."""
    admin = get_supabase_admin()

    # Documents validés (sur toute la durée de vie, pas seulement le mois)
    tasks = (
        admin.table("tasks")
        .select("review_status, status")
        .eq("organization_id", organization_id)
        .eq("status", "completed")
        .execute()
    )
    rows = tasks.data or []
    approved = sum(1 for t in rows if t.get("review_status") == "approved")
    rejected = sum(1 for t in rows if t.get("review_status") == "rejected")
    reviewed = approved + rejected
    approval_rate = round(approved / reviewed * 100) if reviewed else 0

    eligible = approved >= CERT_MIN_APPROVED_DOCS and approval_rate >= CERT_MIN_APPROVAL_RATE

    level = None
    label = None
    if eligible:
        for threshold, lvl, lbl in CERT_LEVELS:
            if approved >= threshold:
                level, label = lvl, lbl
                break

    return {
        "eligible": eligible,
        "level": level,
        "label": label,
        "approved_docs": approved,
        "approval_rate": approval_rate,
        "criteria": {
            "min_approved": CERT_MIN_APPROVED_DOCS,
            "min_approval_rate": CERT_MIN_APPROVAL_RATE,
        },
        "progress_to_next": _progress_to_next(approved),
    }


def _progress_to_next(approved: int) -> dict[str, Any] | None:
    """Combien de documents avant le niveau supérieur."""
    for threshold, lvl, _ in reversed(CERT_LEVELS):
        if approved < threshold:
            return {"next_level": lvl, "docs_needed": threshold - approved, "at": threshold}
    return None  # déjà au niveau max


def get_or_create_badge_token(organization_id: str) -> str:
    """Retourne un identifiant public stable pour le badge (pour l'URL de vérif)."""
    # Hash déterministe de l'org_id → identifiant public non devinable mais stable
    return hashlib.sha256(f"betagent-cert-{organization_id}".encode()).hexdigest()[:16]


def verify_badge(badge_token: str) -> dict[str, Any]:
    """Vérifie un badge depuis son token public (page publique de vérification)."""
    admin = get_supabase_admin()

    # Retrouve l'org correspondant au token (on doit scanner — peu d'orgs)
    orgs = admin.table("organizations").select("id, name").execute()
    for org in orgs.data or []:
        if get_or_create_badge_token(org["id"]) == badge_token:
            cert = compute_certification(org["id"])
            if cert["eligible"]:
                return {
                    "valid": True,
                    "organization_name": org["name"],
                    "level": cert["level"],
                    "label": cert["label"],
                    "approved_docs": cert["approved_docs"],
                    "verified_at": datetime.utcnow().isoformat(),
                }
            return {"valid": False, "reason": "Certification non active"}
    return {"valid": False, "reason": "Badge inconnu"}


def get_badge_embed_html(organization_id: str) -> str | None:
    """Génère le HTML du badge à coller sur le site du bureau."""
    cert = compute_certification(organization_id)
    if not cert["eligible"]:
        return None
    token = get_or_create_badge_token(organization_id)
    verify_url = f"https://bet-agent.ch/verify/{token}"
    level_color = {"Or": "#C9A227", "Argent": "#8E9099", "Bronze": "#A97142"}.get(cert["level"], "#1B3A5C")
    return f"""<a href="{verify_url}" target="_blank" rel="noopener" \
style="display:inline-flex;align-items:center;gap:8px;padding:8px 14px;\
border:1px solid {level_color};border-radius:8px;text-decoration:none;\
font-family:sans-serif;font-size:13px;color:#1B3A5C;background:#fff;">
  <span style="font-weight:600;color:{level_color};">✓ BET Agent</span>
  <span style="color:#525252;">Bureau certifié {cert['level']}</span>
</a>"""
