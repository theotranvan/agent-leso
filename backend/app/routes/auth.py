"""Routes d'authentification et gestion de l'organisation."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.database import get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user, limiter
from app.models.organization import Organization
from app.models.user import User, UserCreate, UserInvite

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: UserCreate):
    """Crée un compte + une organisation.

    L'utilisateur Supabase auth.users doit être créé CÔTÉ FRONTEND via supabase.auth.signUp().
    Cette route crée ensuite l'organization + la ligne users liée.
    """
    admin = get_supabase_admin()

    # 1. Crée le user Supabase auth
    try:
        auth_user = admin.auth.admin.create_user({
            "email": body.email,
            "password": body.password,
            "email_confirm": True,
            "user_metadata": {"full_name": body.full_name},
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Création compte échouée : {e}")

    user_id = auth_user.user.id

    # 2. Crée l'organisation (avec contexte CH)
    org_name = body.organization_name or (body.full_name or body.email.split("@")[0])
    # Défauts selon pays
    country = body.country or "CH"
    default_vat = 8.10 if country == "CH" else 20.0
    default_currency = "CHF" if country == "CH" else "EUR"
    try:
        org = admin.table("organizations").insert({
            "name": org_name,
            "email": body.email,
            "plan": "starter",
            "tasks_limit": settings.PLAN_LIMITS["starter"]["tasks"],
            "country": country,
            "canton": body.canton,
            "language": body.language or "fr",
            "currency": body.currency or default_currency,
            "vat_number": body.vat_number,
            "vat_rate": default_vat,
            "address": body.address,
            "postal_code": body.postal_code,
            "city": body.city,
        }).execute()
        org_id = org.data[0]["id"]
    except Exception as e:
        admin.auth.admin.delete_user(user_id)
        raise HTTPException(status_code=500, detail=f"Création organisation échouée : {e}")

    # 3. Crée la ligne users (admin par défaut)
    admin.table("users").insert({
        "id": user_id,
        "organization_id": org_id,
        "role": "admin",
        "full_name": body.full_name,
    }).execute()

    # 4. Crée customer Stripe (asynchrone, non bloquant)
    try:
        from app.services.stripe_service import create_customer
        customer_id = create_customer(body.email, org_name, org_id)
        admin.table("organizations").update({"stripe_customer_id": customer_id}).eq("id", org_id).execute()
    except Exception as e:
        logger.warning(f"Création customer Stripe échouée (non bloquant) : {e}")

    await audit_log(
        action="user_registered",
        organization_id=org_id,
        user_id=user_id,
        ip_address=request.client.host if request.client else None,
    )

    return {"user_id": user_id, "organization_id": org_id, "email": body.email}


@router.get("/me")
async def me(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Retourne l'utilisateur courant + son organisation."""
    admin = get_supabase_admin()
    u = admin.table("users").select("*").eq("id", user.id).maybe_single().execute()
    org = admin.table("organizations").select("*").eq("id", user.organization_id).maybe_single().execute()
    return {
        "user": u.data,
        "organization": org.data,
    }


@router.post("/invite")
async def invite_user(
    body: UserInvite,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    """Invite un utilisateur dans l'organisation (admin uniquement)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Droits admin requis")

    admin = get_supabase_admin()

    # Crée user Supabase (email avec lien de confirmation envoyé automatiquement)
    try:
        invite_response = admin.auth.admin.invite_user_by_email(
            body.email,
            options={"data": {"organization_id": user.organization_id, "role": body.role}},
        )
        new_user_id = invite_response.user.id
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invitation échouée : {e}")

    # Lien users
    admin.table("users").insert({
        "id": new_user_id,
        "organization_id": user.organization_id,
        "role": body.role,
    }).execute()

    await audit_log(
        action="user_invited",
        organization_id=user.organization_id,
        user_id=user.id,
        metadata={"invited_email": body.email, "role": body.role},
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "invited", "user_id": new_user_id, "email": body.email}


@router.delete("/me")
async def delete_my_account(
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    """RGPD : suppression complète du compte et des données (admin seulement pour son org)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Seul un admin peut supprimer l'organisation")

    admin = get_supabase_admin()
    org_id = user.organization_id

    # Log avant suppression
    await audit_log(
        action="organization_deleted",
        organization_id=org_id,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )

    # Suppression cascade via FK ON DELETE CASCADE
    admin.table("organizations").delete().eq("id", org_id).execute()

    # Suppression users Supabase auth
    users_of_org = admin.table("users").select("id").eq("organization_id", org_id).execute()
    for u in users_of_org.data or []:
        try:
            admin.auth.admin.delete_user(u["id"])
        except Exception as e:
            logger.warning(f"Erreur suppression auth.users {u['id']}: {e}")

    return {"status": "deleted"}


@router.get("/export")
async def export_data(user: Annotated[AuthUser, Depends(get_current_user)]):
    """RGPD : export complet des données de l'organisation (JSON)."""
    admin = get_supabase_admin()
    org_id = user.organization_id

    organization = admin.table("organizations").select("*").eq("id", org_id).maybe_single().execute().data
    users = admin.table("users").select("*").eq("organization_id", org_id).execute().data
    projects = admin.table("projects").select("*").eq("organization_id", org_id).execute().data
    documents = admin.table("documents").select("*").eq("organization_id", org_id).execute().data
    tasks = admin.table("tasks").select("*").eq("organization_id", org_id).execute().data
    logs = admin.table("audit_logs").select("*").eq("organization_id", org_id).limit(1000).execute().data

    return {
        "organization": organization,
        "users": users,
        "projects": projects,
        "documents": documents,
        "tasks": tasks,
        "audit_logs": logs,
    }
