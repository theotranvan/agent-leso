"""Intégration Stripe pour la facturation SaaS."""
import logging

import stripe

from app.config import settings
from app.database import get_supabase_admin

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# Vocabulaire unique solo/bureau/enterprise. Les noms des variables d'env Stripe
# (STRIPE_PRICE_STARTER/PRO/ENTERPRISE) restent inchangés : ce ne sont que des
# identifiants pointant vers les objets Price du dashboard Stripe.
# Deux intervalles : "monthly" (mensuel) et "yearly" (annuel, −17 %).
PLAN_TO_PRICE_ID = {
    "monthly": {
        "solo": settings.STRIPE_PRICE_STARTER,
        "bureau": settings.STRIPE_PRICE_PRO,
        "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
    },
    "yearly": {
        "solo": settings.STRIPE_PRICE_STARTER_YEARLY,
        "bureau": settings.STRIPE_PRICE_PRO_YEARLY,
        "enterprise": settings.STRIPE_PRICE_ENTERPRISE_YEARLY,
    },
}

# Tout price_id (mensuel OU annuel) → plan, pour les webhooks de souscription.
PRICE_ID_TO_PLAN = {
    pid: plan
    for interval in PLAN_TO_PRICE_ID.values()
    for plan, pid in interval.items()
    if pid
}


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
    interval: str = "monthly",
) -> str:
    """Crée une session Stripe Checkout. Retourne l'URL.

    `interval` : "monthly" (défaut) ou "yearly" (−17 %). Si le prix annuel n'est
    pas encore configuré dans Stripe, lève une ValueError explicite plutôt que
    de facturer silencieusement au tarif mensuel.
    """
    interval = interval if interval in PLAN_TO_PRICE_ID else "monthly"
    price_id = PLAN_TO_PRICE_ID[interval].get(plan)
    if not price_id:
        if interval == "yearly":
            raise ValueError(
                "La facturation annuelle n'est pas encore disponible pour ce plan. "
                "Choisissez le mensuel ou contactez-nous."
            )
        raise ValueError(f"Plan inconnu: {plan}")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"organization_id": organization_id, "plan": plan, "interval": interval},
        subscription_data={"metadata": {"organization_id": organization_id, "plan": plan, "interval": interval}},
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
    session_type = session.get("metadata", {}).get("type", "subscription")
    customer_id = session.get("customer")

    if not organization_id:
        logger.error("Webhook checkout sans organization_id")
        return

    # V5 : traitement des credit packs (one-shot payment, pas subscription)
    if session_type == "credit_pack":
        try:
            import asyncio

            from app.services.token_quota import (
                CREDIT_PACK_PRICE_CHF,
                CREDIT_PACK_TOKENS,
                add_credit_pack,
            )

            quantity = int(session.get("metadata", {}).get("quantity", 1) or 1)
            tokens = int(session.get("metadata", {}).get("tokens_per_pack", CREDIT_PACK_TOKENS) or CREDIT_PACK_TOKENS)

            coro = add_credit_pack(
                organization_id=organization_id,
                stripe_session_id=session["id"],
                stripe_payment_intent_id=session.get("payment_intent"),
                tokens=tokens * quantity,
                price_chf=CREDIT_PACK_PRICE_CHF * quantity,
            )
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(coro)
                else:
                    loop.run_until_complete(coro)
            except RuntimeError:
                asyncio.run(coro)

            logger.info("Credit pack enregistré : org=%s x%d", organization_id, quantity)
        except Exception as e:
            logger.exception("Enregistrement credit pack échoué : %s", e)
        return

    # Subscription classique
    from app.services.token_quota import DEFAULT_PLAN, QUOTA_PLANS
    plan = session.get("metadata", {}).get("plan", DEFAULT_PLAN)
    subscription_id = session.get("subscription")

    admin = get_supabase_admin()
    # V5 : on utilise les quotas tokens au lieu des tasks_limit
    tokens_limit = QUOTA_PLANS.get(plan, QUOTA_PLANS[DEFAULT_PLAN])

    admin.table("organizations").update({
        "plan": plan,
        "tokens_limit_monthly": tokens_limit,
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "active": True,
    }).eq("id", organization_id).execute()

    logger.info(f"Organisation {organization_id} activée sur plan {plan} ({tokens_limit:,} tokens/mois)")


def _handle_subscription_updated(subscription: dict) -> None:
    organization_id = subscription.get("metadata", {}).get("organization_id")
    if not organization_id:
        customer_id = subscription.get("customer")
        admin = get_supabase_admin()
        result = admin.table("organizations").select("id").eq("stripe_customer_id", customer_id).maybe_single().execute()
        if not result.data:
            return
        organization_id = result.data["id"]

    items = subscription.get("items", {}).get("data", [])
    if not items:
        return
    from app.services.token_quota import DEFAULT_PLAN, QUOTA_PLANS
    price_id = items[0].get("price", {}).get("id")
    plan = PRICE_ID_TO_PLAN.get(price_id, DEFAULT_PLAN)

    status = subscription.get("status")
    active = status in ("active", "trialing")

    tokens_limit = QUOTA_PLANS.get(plan, QUOTA_PLANS[DEFAULT_PLAN])

    admin = get_supabase_admin()
    admin.table("organizations").update({
        "plan": plan,
        "tokens_limit_monthly": tokens_limit,
        "stripe_subscription_id": subscription["id"],
        "active": active,
    }).eq("id", organization_id).execute()
    logger.info("Subscription updated: org=%s plan=%s active=%s", organization_id, plan, active)


def _handle_subscription_deleted(subscription: dict) -> None:
    customer_id = subscription.get("customer")
    admin = get_supabase_admin()
    admin.table("organizations").update({
        "active": False,
        "stripe_subscription_id": None,
    }).eq("stripe_customer_id", customer_id).execute()


def _handle_payment_failed(invoice: dict) -> None:
    customer_id = invoice.get("customer")
    attempt_count = invoice.get("attempt_count", 1)
    admin = get_supabase_admin()
    result = admin.table("organizations").select("id, email, name").eq("stripe_customer_id", customer_id).maybe_single().execute()

    if not result.data:
        return

    try:
        from app.services.email_service import send_alert_email
        send_alert_email(
            to=[result.data["email"]],
            subject="Paiement échoué — action requise",
            body_html="<p>Le paiement de votre abonnement LESO a échoué.</p><p>Merci de mettre à jour votre moyen de paiement dans votre espace client.</p>",
        )
    except Exception as e:
        logger.warning("Email paiement échoué : %s", e)

    # Suspend after 2nd failed attempt (Stripe retries 3–4 times before deleting subscription)
    if attempt_count >= 2:
        admin.table("organizations").update({"active": False}).eq(
            "id", result.data["id"],
        ).execute()
        logger.warning("Organisation %s suspendue après %d échecs de paiement", result.data["id"], attempt_count)


def create_credit_pack_session(
    customer_id: str,
    organization_id: str,
    quantity: int = 1,
) -> str:
    """Crée une session Stripe one-shot pour l'achat d'un/plusieurs credit packs.

    Chaque pack = ~100 livrables additionnels = 200 CHF. Mode 'payment' (pas d'abonnement).
    """
    from app.services.token_quota import (
        CREDIT_PACK_LIVRABLES,
        CREDIT_PACK_PRICE_CHF,
        CREDIT_PACK_TOKENS,
    )

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "chf",
                "product_data": {
                    "name": f"Pack LESO — ~{CREDIT_PACK_LIVRABLES} livrables additionnels",
                    "description": "Livrables supplémentaires consommés après le quota mensuel",
                },
                "unit_amount": CREDIT_PACK_PRICE_CHF * 100,  # en centimes CHF
            },
            "quantity": quantity,
        }],
        metadata={
            "type": "credit_pack",
            "organization_id": organization_id,
            "tokens_per_pack": CREDIT_PACK_TOKENS,
            "quantity": quantity,
        },
        success_url=f"{settings.FRONTEND_URL}/settings/billing?pack_purchased=1",
        cancel_url=f"{settings.FRONTEND_URL}/settings/billing?cancelled=1",
    )
    return session.url
