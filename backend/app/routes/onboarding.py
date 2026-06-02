"""Routes onboarding — wizard d'accueil pour les nouvelles organisations.

Parcours en 3 étapes :
  1. Organisation : nom du bureau, canton principal, taille
  2. Charte graphique : logo + couleurs (réutilise le système de branding)
  3. Premier projet : crée une première affaire pour démarrer immédiatement

À la fin, onboarding_completed passe à TRUE et l'utilisateur arrive sur un
dashboard déjà peuplé plutôt qu'un écran vide.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_supabase_admin
from app.middleware import AuthUser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/state")
async def get_onboarding_state(user: Annotated[AuthUser, Depends(get_current_user)]):
    """État courant de l'onboarding pour cette organisation."""
    admin = get_supabase_admin()
    org = (
        admin.table("organizations")
        .select("name, onboarding_completed, onboarding_step, canton, branding_config")
        .eq("id", user.organization_id).maybe_single().execute()
    )
    o = org.data or {}
    has_branding = bool((o.get("branding_config") or {}).get("primary_color"))
    has_project = bool(
        (admin.table("projects").select("id", count="exact")
         .eq("organization_id", user.organization_id).limit(1).execute()).data
    )
    return {
        "completed": o.get("onboarding_completed", False),
        "step": o.get("onboarding_step", 0),
        "steps": [
            {"key": "organization", "label": "Votre bureau",
             "done": bool(o.get("name")) and bool(o.get("canton"))},
            {"key": "branding", "label": "Charte graphique", "done": has_branding},
            {"key": "first_project", "label": "Première affaire", "done": has_project},
        ],
    }


@router.post("/step/organization")
async def onboarding_organization(
    user: Annotated[AuthUser, Depends(get_current_user)],
    body: dict,
):
    """Étape 1 — Informations du bureau."""
    if user.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur")

    admin = get_supabase_admin()
    update = {"onboarding_step": 1}
    for field in ("name", "canton"):
        if body.get(field):
            update[field] = body[field]
    if body.get("team_size"):
        update["team_size"] = body["team_size"]

    admin.table("organizations").update(update).eq("id", user.organization_id).execute()
    return {"step": 1, "next": "branding"}


@router.post("/step/branding")
async def onboarding_branding(
    user: Annotated[AuthUser, Depends(get_current_user)],
    body: dict,
):
    """Étape 2 — Charte graphique (logo + couleurs)."""
    admin = get_supabase_admin()
    branding = {
        "primary_color": body.get("primary_color", "#1B3A5C"),
        "accent_color": body.get("accent_color", "#2E75B6"),
        "full_name": body.get("full_name", ""),
        "footer_text": body.get("footer_text", ""),
        "logo_url": body.get("logo_url", ""),
    }
    admin.table("organizations").update({
        "branding_config": branding,
        "onboarding_step": 2,
    }).eq("id", user.organization_id).execute()
    return {"step": 2, "next": "first_project"}


@router.post("/step/first-project")
async def onboarding_first_project(
    user: Annotated[AuthUser, Depends(get_current_user)],
    body: dict,
):
    """Étape 3 — Création de la première affaire."""
    admin = get_supabase_admin()
    project = {
        "organization_id": user.organization_id,
        "name": body.get("name", "Ma première affaire"),
        "address": body.get("address", ""),
        "commune": body.get("commune", ""),
        "canton": body.get("canton", "VD"),
        "sre_m2": body.get("sre_m2"),
        "nb_logements": body.get("nb_logements"),
        "affectation": body.get("affectation", ""),
        "labels": body.get("labels", []),
        "current_phase": body.get("phase_sia_demarrage", "avant_projet"),
        "status": "active",
    }
    result = admin.table("projects").insert(project).execute()
    project_id = (result.data or [{}])[0].get("id")

    # Marque l'onboarding terminé
    admin.table("organizations").update({
        "onboarding_step": 3,
        "onboarding_completed": True,
    }).eq("id", user.organization_id).execute()

    return {"step": 3, "completed": True, "project_id": project_id}


@router.post("/skip")
async def skip_onboarding(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Permet de passer l'onboarding (l'utilisateur garde la main)."""
    admin = get_supabase_admin()
    admin.table("organizations").update({
        "onboarding_completed": True,
    }).eq("id", user.organization_id).execute()
    return {"completed": True, "skipped": True}
