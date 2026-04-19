"""Intégration Stripe pour la facturation SaaS."""
import logging
from typing import Optional

import stripe

from app.config import settings
from app.database import get_supabase_admin

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

PLAN_TO_PRICE_ID = {
    "starter": settings.STRIPE_PRICE_STARTER,
    "pro": settings.STRIPE_PRICE_PRO,
    "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
}

PRICE_ID_TO_PLAN = {v: k for k, v in PLAN_TO_PRICE_ID.items()}


def create_customer(email: str, organization_name: str, organization_id: str) -> str:
    """Crée un customer Stripe."""
    customer = stripe.Customer.create(
        email=email,
        name=organization_name,
        metadata={"organization_id": organization_id},
    )
    return customer.id


def create_checkout_session(
    customer_id: str,
    plan: str,
    organization_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Crée une session Stripe Checkout. Retourne l'URL."""
    price_id = PLAN_TO_PRICE_ID.get(plan)
    if not price_id:
        raise ValueError(f"Plan inconnu: {plan}")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"organization_id": organization_id, "plan": plan},
        subscription_data={"metadata": {"organization_id": organization_id, "plan": plan}},
        allow_promotion_codes=True,
        billing_address_collection="required",
    )
    return session.url


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    """Portail client Stripe (gestion moyens de paiement, factures, annulation)."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def verify_webhook_signature(payload: bytes, signature: str) -> stripe.Event:
    """Vérifie la signature d'un webhook Stripe."""
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )


def handle_webhook_event(event: stripe.Event) -> None:
    """Route les événements webhook Stripe vers les handlers appropriés."""
    event_type = event["type"]
    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(event["data"]["object"])
    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        _handle_subscription_updated(event["data"]["object"])
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(event["data"]["object"])
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(event["data"]["object"])


def _handle_checkout_completed(session: dict) -> None:
    organization_id = session.get("metadata", {}).get("organization_id")
    plan = session.get("metadata", {}).get("plan", "starter")
    subscription_id = session.get("subscription")
    customer_id = session.get("customer")

    if not organization_id:
        logger.error("Webhook checkout sans organization_id")
        return

    admin = get_supabase_admin()
    limits = settings.PLAN_LIMITS.get(plan, {"tasks": 500})
    admin.table("organizations").update({
        "plan": plan,
        "tasks_limit": limits["tasks"],
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "active": True,
    }).eq("id", organization_id).execute()

    logger.info(f"Organisation {organization_id} activée sur plan {plan}")


def _handle_subscription_updated(subscription: dict) -> None:
    organization_id = subscription.get("metadata", {}).get("organization_id")
    if not organization_id:
        # Fallback: on cherche via customer_id
        customer_id = subscription.get("customer")
        admin = get_supabase_admin()
        result = admin.table("organizations").select("id").eq("stripe_customer_id", customer_id).maybe_single().execute()
        if not result.data:
            return
        organization_id = result.data["id"]

    # Récupère le price_id et en déduit le plan
    items = subscription.get("items", {}).get("data", [])
    if not items:
        return
    price_id = items[0].get("price", {}).get("id")
    plan = PRICE_ID_TO_PLAN.get(price_id, "starter")

    status = subscription.get("status")
    active = status in ("active", "trialing")

    admin = get_supabase_admin()
    limits = settings.PLAN_LIMITS.get(plan, {"tasks": 500})
    admin.table("organizations").update({
        "plan": plan,
        "tasks_limit": limits["tasks"],
        "stripe_subscription_id": subscription["id"],
        "active": active,
    }).eq("id", organization_id).execute()


def _handle_subscription_deleted(subscription: dict) -> None:
    customer_id = subscription.get("customer")
    admin = get_supabase_admin()
    admin.table("organizations").update({
        "active": False,
        "stripe_subscription_id": None,
    }).eq("stripe_customer_id", customer_id).execute()


def _handle_payment_failed(invoice: dict) -> None:
    customer_id = invoice.get("customer")
    admin = get_supabase_admin()
    result = admin.table("organizations").select("id, email, name").eq("stripe_customer_id", customer_id).maybe_single().execute()

    if result.data:
        # Envoi d'un email d'alerte
        from app.services.email_service import send_alert_email
        send_alert_email(
            to=[result.data["email"]],
            subject="Paiement échoué — action requise",
            body_html=f"<p>Le paiement de votre abonnement BET Agent a échoué.</p><p>Merci de mettre à jour votre moyen de paiement dans votre espace client.</p>",
        )
