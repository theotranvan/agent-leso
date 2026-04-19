"""Routes billing - Stripe Checkout, portail client, webhooks."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.database import get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user
from app.services import stripe_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str  # starter | pro | enterprise


@router.post("/checkout")
async def checkout(
    body: CheckoutRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    """Crée une session Stripe Checkout et retourne l'URL."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Droits admin requis")

    if body.plan not in settings.PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Plan invalide")

    admin = get_supabase_admin()
    org = admin.table("organizations").select("*").eq("id", user.organization_id).maybe_single().execute()
    if not org.data:
        raise HTTPException(status_code=404, detail="Organisation introuvable")

    customer_id = org.data.get("stripe_customer_id")
    if not customer_id:
        customer_id = stripe_service.create_customer(
            email=org.data["email"],
            organization_name=org.data["name"],
            organization_id=user.organization_id,
        )
        admin.table("organizations").update({"stripe_customer_id": customer_id}).eq("id", user.organization_id).execute()

    url = stripe_service.create_checkout_session(
        customer_id=customer_id,
        plan=body.plan,
        organization_id=user.organization_id,
        success_url=f"{settings.FRONTEND_URL}/billing?success=1",
        cancel_url=f"{settings.FRONTEND_URL}/billing?canceled=1",
    )

    await audit_log(
        action="checkout_initiated",
        organization_id=user.organization_id,
        user_id=user.id,
        metadata={"plan": body.plan},
        ip_address=request.client.host if request.client else None,
    )
    return {"checkout_url": url}


@router.post("/portal")
async def portal(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Retourne l'URL du portail client Stripe."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Droits admin requis")

    admin = get_supabase_admin()
    org = admin.table("organizations").select("stripe_customer_id").eq("id", user.organization_id).maybe_single().execute()
    if not org.data or not org.data.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="Aucun compte de facturation actif")

    url = stripe_service.create_billing_portal_session(
        customer_id=org.data["stripe_customer_id"],
        return_url=f"{settings.FRONTEND_URL}/billing",
    )
    return {"portal_url": url}


@router.get("/status")
async def status(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Statut actuel de la facturation et du quota."""
    admin = get_supabase_admin()
    org = admin.table("organizations").select("plan, tasks_used_this_month, tasks_limit, active, stripe_subscription_id").eq("id", user.organization_id).maybe_single().execute()
    if not org.data:
        raise HTTPException(status_code=404, detail="Organisation introuvable")

    return {
        **org.data,
        "plan_details": settings.PLAN_LIMITS.get(org.data["plan"], {}),
        "quota_pct": round(100 * (org.data["tasks_used_this_month"] / max(org.data["tasks_limit"], 1)), 1),
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str, Header(alias="Stripe-Signature")],
):
    """Webhook Stripe - signature vérifiée, puis dispatch événement."""
    payload = await request.body()
    try:
        event = stripe_service.verify_webhook_signature(payload, stripe_signature)
    except Exception as e:
        logger.error(f"Signature webhook invalide: {e}")
        raise HTTPException(status_code=400, detail="Signature invalide")

    try:
        stripe_service.handle_webhook_event(event)
    except Exception as e:
        logger.exception(f"Erreur handler webhook: {e}")
        # On ne lève pas d'erreur pour que Stripe ne re-retry pas indéfiniment sur une erreur applicative
        return {"received": True, "error": str(e)}

    return {"received": True}
