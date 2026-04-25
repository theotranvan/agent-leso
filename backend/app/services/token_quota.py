"""Service de gestion des quotas tokens par organisation.

Architecture
============
Chaque organisation a :
  - `tokens_limit_monthly` : quota du plan actuel (pilot/pro/scale)
  - `tokens_used_current_month` : consommation du mois (reset le 1er)
  - `tokens_pack_remaining` : tokens additionnels achetés via credit packs

Ordre de consommation :
  1. D'abord sur le quota mensuel (jusqu'à `tokens_limit_monthly`)
  2. Puis sur `tokens_pack_remaining` si des packs existent
  3. Si les deux sont à zéro → TokenQuotaExceeded

Logging
=======
Chaque appel LLM passe par `log_token_usage()` qui :
  - Insère une ligne dans `token_usage`
  - Incrémente `tokens_used_current_month` (ou décrémente pack si mois dépassé)
  - Déclenche une alerte Slack à 80% puis 100% (déduplication via
    `last_quota_alert_pct` sur organizations)

Exceptions
==========
`TokenQuotaExceeded` : levée AVANT appel LLM par `check_quota_available()`.
Hérite de ValueError pour remontée propre vers route → HTTP 429.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ==========================================================================
# CONSTANTES — demandées par le cahier des charges
# ==========================================================================

QUOTA_PLANS: dict[str, int] = {
    "pilot": 8_000_000,
    "pro": 20_000_000,
    "scale": 60_000_000,
}

CREDIT_PACK_TOKENS = 5_000_000
CREDIT_PACK_PRICE_CHF = 200

# Seuils d'alerte (en % du quota mensuel)
ALERT_THRESHOLDS_PCT = (80, 100)

# Prix Stripe du credit pack - à créer dans le dashboard Stripe avec cet ID
STRIPE_CREDIT_PACK_PRICE_ID = "price_credit_pack_5M_CHF200"


# ==========================================================================
# EXCEPTION
# ==========================================================================

class TokenQuotaExceeded(Exception):
    """Levée quand l'organisation n'a plus de tokens disponibles.

    Attributes:
        organization_id: orga concernée
        tokens_used: consommation mois courant
        tokens_limit: quota mensuel
        tokens_pack_remaining: tokens additionnels dispos
        user_message: message user-friendly
    """

    def __init__(
        self,
        organization_id: str,
        tokens_used: int,
        tokens_limit: int,
        tokens_pack_remaining: int = 0,
    ) -> None:
        self.organization_id = organization_id
        self.tokens_used = tokens_used
        self.tokens_limit = tokens_limit
        self.tokens_pack_remaining = tokens_pack_remaining

        overage = tokens_used - tokens_limit
        self.user_message = (
            f"Quota mensuel atteint : {tokens_used:,} / {tokens_limit:,} tokens "
            f"({overage:,} au-delà). Tu peux acheter un pack de {CREDIT_PACK_TOKENS:,} tokens "
            f"pour {CREDIT_PACK_PRICE_CHF} CHF dans Paramètres → Facturation, "
            f"ou attendre le {_next_month_str()} pour le reset automatique."
        )
        super().__init__(self.user_message)


def _next_month_str() -> str:
    """Date du prochain reset (1er du mois suivant)."""
    now = datetime.utcnow()
    if now.month == 12:
        return f"1er janvier {now.year + 1}"
    next_month = now.replace(month=now.month + 1, day=1)
    months_fr = ["", "janvier", "février", "mars", "avril", "mai", "juin",
                 "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"1er {months_fr[next_month.month]}"


# ==========================================================================
# CHECK — à appeler avant dispatch
# ==========================================================================

async def check_quota_available(
    organization_id: str,
    estimated_tokens: int = 0,
) -> dict[str, Any]:
    """Vérifie que l'organisation a assez de tokens pour une tâche.

    Lève `TokenQuotaExceeded` si quota mensuel + packs remaining < estimated_tokens.

    `estimated_tokens=0` (défaut) permet de vérifier uniquement qu'il reste
    des tokens, sans exiger un minimum — utile au démarrage d'une tâche dont
    on ne connaît pas le volume exact.

    Retourne un dict avec l'état courant :
      {tokens_used, tokens_limit, tokens_pack_remaining, tokens_total_available,
       used_pct, plan}
    """
    from app.database import get_supabase_admin

    admin = get_supabase_admin()
    org = admin.table("organizations").select(
        "id, plan, tokens_limit_monthly, tokens_used_current_month, "
        "tokens_pack_remaining, current_month_started_at"
    ).eq("id", organization_id).maybe_single().execute()

    if not org.data:
        raise ValueError(f"Organisation {organization_id} introuvable")

    # Reset auto si mois changé
    started = org.data.get("current_month_started_at")
    if started:
        started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        if started_dt.month != datetime.utcnow().month or started_dt.year != datetime.utcnow().year:
            admin.table("organizations").update({
                "tokens_used_current_month": 0,
                "last_quota_alert_at": None,
                "last_quota_alert_pct": None,
                "current_month_started_at": datetime.utcnow().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0,
                ).isoformat(),
            }).eq("id", organization_id).execute()
            org.data["tokens_used_current_month"] = 0

    tokens_used = int(org.data.get("tokens_used_current_month") or 0)
    tokens_limit = int(org.data.get("tokens_limit_monthly") or QUOTA_PLANS["pilot"])
    tokens_pack = int(org.data.get("tokens_pack_remaining") or 0)
    remaining_monthly = max(0, tokens_limit - tokens_used)
    total_available = remaining_monthly + tokens_pack

    if total_available <= estimated_tokens:
        logger.warning(
            "Quota exceeded org=%s used=%d limit=%d pack=%d estimated=%d",
            organization_id, tokens_used, tokens_limit, tokens_pack, estimated_tokens,
        )
        raise TokenQuotaExceeded(
            organization_id=organization_id,
            tokens_used=tokens_used,
            tokens_limit=tokens_limit,
            tokens_pack_remaining=tokens_pack,
        )

    used_pct = int((tokens_used / max(tokens_limit, 1)) * 100) if tokens_limit else 0

    return {
        "tokens_used": tokens_used,
        "tokens_limit": tokens_limit,
        "tokens_pack_remaining": tokens_pack,
        "tokens_total_available": total_available,
        "used_pct": used_pct,
        "plan": org.data.get("plan") or "pilot",
    }


# ==========================================================================
# LOG — à appeler APRÈS chaque appel LLM
# ==========================================================================

async def log_token_usage(
    organization_id: str,
    task_id: Optional[str],
    task_type: Optional[str],
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_chf: float,
    fallback_used: bool = False,
    is_regeneration: bool = False,
    regeneration_reason: Optional[str] = None,
    regeneration_sections: Optional[list[str]] = None,
    regeneration_attempt: int = 0,
) -> None:
    """Log un appel LLM dans token_usage + met à jour les compteurs org.

    Ne lève jamais d'exception (fail-soft) — l'échec du log ne doit pas
    bloquer la livraison de la tâche au user.
    """
    try:
        from app.database import get_supabase_admin
        admin = get_supabase_admin()
        tokens_total = tokens_in + tokens_out

        # 1. Insert dans token_usage
        admin.table("token_usage").insert({
            "organization_id": organization_id,
            "task_id": task_id,
            "task_type": task_type,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_chf": cost_chf,
            "fallback_used": fallback_used,
            "is_regeneration": is_regeneration,
            "regeneration_reason": regeneration_reason,
            "regeneration_sections": regeneration_sections,
            "regeneration_attempt": regeneration_attempt,
        }).execute()

        # 2. Update compteurs — d'abord quota mensuel, puis pack si dépassé
        org = admin.table("organizations").select(
            "tokens_limit_monthly, tokens_used_current_month, tokens_pack_remaining, "
            "last_quota_alert_pct"
        ).eq("id", organization_id).maybe_single().execute()

        if not org.data:
            return

        used = int(org.data.get("tokens_used_current_month") or 0)
        limit = int(org.data.get("tokens_limit_monthly") or QUOTA_PLANS["pilot"])
        pack = int(org.data.get("tokens_pack_remaining") or 0)
        last_alert_pct = int(org.data.get("last_quota_alert_pct") or 0)

        remaining_monthly = max(0, limit - used)

        if tokens_total <= remaining_monthly:
            # 100% sur quota mensuel
            new_used = used + tokens_total
            new_pack = pack
        else:
            # Partie sur quota mensuel + partie sur pack
            on_pack = tokens_total - remaining_monthly
            new_used = limit  # saturé
            new_pack = max(0, pack - on_pack)

        update_fields: dict[str, Any] = {
            "tokens_used_current_month": new_used,
            "tokens_pack_remaining": new_pack,
        }

        # 3. Check seuils d'alerte
        new_used_pct = int((new_used / max(limit, 1)) * 100)
        for threshold in ALERT_THRESHOLDS_PCT:
            if new_used_pct >= threshold > last_alert_pct:
                await _send_quota_alert(admin, organization_id, new_used, limit, threshold)
                update_fields["last_quota_alert_at"] = datetime.utcnow().isoformat()
                update_fields["last_quota_alert_pct"] = threshold
                break  # une alerte par événement

        admin.table("organizations").update(update_fields).eq("id", organization_id).execute()

        # 4. Si régénération : update tasks.regeneration_history
        if is_regeneration and task_id:
            try:
                task = admin.table("tasks").select("regeneration_history").eq(
                    "id", task_id,
                ).maybe_single().execute()
                history = task.data.get("regeneration_history") if task.data else []
                history = history or []
                history.append({
                    "at": datetime.utcnow().isoformat(),
                    "reason": regeneration_reason,
                    "sections": regeneration_sections or [],
                    "attempt": regeneration_attempt,
                    "model_used": model,
                    "tokens": tokens_total,
                    "cost_chf": cost_chf,
                })
                admin.table("tasks").update({
                    "regeneration_history": history,
                    "regeneration_count": regeneration_attempt,
                    "last_regenerated_at": datetime.utcnow().isoformat(),
                }).eq("id", task_id).execute()
            except Exception as exc:
                logger.debug("Update regen history échec : %s", exc)

    except Exception as e:
        logger.warning("log_token_usage échec : %s", e)


# ==========================================================================
# ALERTE SLACK
# ==========================================================================

async def _send_quota_alert(
    admin: Any,
    organization_id: str,
    tokens_used: int,
    tokens_limit: int,
    threshold_pct: int,
) -> None:
    """Envoie une alerte Slack interne sur le webhook admin."""
    webhook_url = getattr(settings, "SLACK_WEBHOOK_URL", None) or ""
    if not webhook_url:
        logger.info("Slack webhook non configuré, alerte org=%s quota=%d%% ignorée",
                    organization_id, threshold_pct)
        return

    try:
        org = admin.table("organizations").select("name, email, plan").eq(
            "id", organization_id,
        ).maybe_single().execute()
        org_name = org.data.get("name", organization_id) if org.data else organization_id
        org_email = org.data.get("email", "?") if org.data else "?"
        plan = org.data.get("plan", "pilot") if org.data else "pilot"

        emoji = "🚨" if threshold_pct >= 100 else "⚠️"
        status = "DÉPASSÉ" if threshold_pct >= 100 else f"{threshold_pct}% atteint"
        action_hint = (
            "L'organisation est bloquée tant qu'elle n'achète pas de credit pack."
            if threshold_pct >= 100
            else "Relance commerciale pour upsell ou achat de pack."
        )

        payload = {
            "text": f"{emoji} Quota tokens BET Agent — {status}",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"{emoji} Quota {status}"},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Organisation :*\n{org_name}"},
                        {"type": "mrkdwn", "text": f"*Plan :*\n{plan}"},
                        {"type": "mrkdwn", "text": f"*Email :*\n{org_email}"},
                        {"type": "mrkdwn", "text": f"*Consommation :*\n{tokens_used:,} / {tokens_limit:,}"},
                    ],
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": f"_{action_hint}_"}],
                },
            ],
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code >= 300:
                logger.warning("Slack webhook HTTP %d : %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("Envoi alerte Slack échec : %s", e)


# ==========================================================================
# USAGE / RAPPORT MENSUEL
# ==========================================================================

async def get_monthly_usage(organization_id: str) -> dict[str, Any]:
    """Retourne la consommation du mois courant pour affichage frontend."""
    from app.database import get_supabase_admin
    admin = get_supabase_admin()

    org = admin.table("organizations").select(
        "plan, tokens_limit_monthly, tokens_used_current_month, tokens_pack_remaining"
    ).eq("id", organization_id).maybe_single().execute()
    if not org.data:
        raise ValueError("Organisation introuvable")

    plan = org.data.get("plan") or "pilot"
    limit = int(org.data.get("tokens_limit_monthly") or QUOTA_PLANS.get(plan, QUOTA_PLANS["pilot"]))
    used = int(org.data.get("tokens_used_current_month") or 0)
    pack = int(org.data.get("tokens_pack_remaining") or 0)

    used_pct = int((used / max(limit, 1)) * 100) if limit else 0
    remaining_monthly = max(0, limit - used)

    # Coût estimé mois courant via view
    start_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage_month = admin.table("token_usage").select(
        "model, tokens_in, tokens_out, cost_chf"
    ).eq("organization_id", organization_id).gte(
        "created_at", start_month.isoformat(),
    ).execute()

    cost_chf_month = sum(float(row.get("cost_chf") or 0) for row in (usage_month.data or []))
    by_model: dict[str, dict[str, Any]] = {}
    for row in usage_month.data or []:
        m = row["model"]
        if m not in by_model:
            by_model[m] = {"tokens": 0, "cost_chf": 0, "calls": 0}
        by_model[m]["tokens"] += (row.get("tokens_in") or 0) + (row.get("tokens_out") or 0)
        by_model[m]["cost_chf"] += float(row.get("cost_chf") or 0)
        by_model[m]["calls"] += 1

    # Packs actifs
    packs_q = admin.table("credit_packs").select("*").eq(
        "organization_id", organization_id,
    ).order("purchased_at", desc=True).limit(20).execute()

    return {
        "plan": plan,
        "month": start_month.strftime("%Y-%m"),
        "tokens_used": used,
        "tokens_limit": limit,
        "tokens_pack_remaining": pack,
        "tokens_total_available": remaining_monthly + pack,
        "used_pct": used_pct,
        "cost_chf_estimated": round(cost_chf_month, 2),
        "by_model": by_model,
        "credit_packs": packs_q.data or [],
        "pack_info": {
            "tokens_per_pack": CREDIT_PACK_TOKENS,
            "price_chf_per_pack": CREDIT_PACK_PRICE_CHF,
        },
    }


# ==========================================================================
# ACHAT D'UN PACK (appelé par webhook Stripe)
# ==========================================================================

async def add_credit_pack(
    organization_id: str,
    stripe_session_id: str,
    stripe_payment_intent_id: Optional[str] = None,
    tokens: int = CREDIT_PACK_TOKENS,
    price_chf: float = CREDIT_PACK_PRICE_CHF,
) -> dict[str, Any]:
    """Enregistre un pack acheté + incrémente tokens_pack_remaining.

    Idempotent via stripe_session_id.
    """
    from app.database import get_supabase_admin
    admin = get_supabase_admin()

    # Idempotence
    existing = admin.table("credit_packs").select("id").eq(
        "stripe_session_id", stripe_session_id,
    ).maybe_single().execute()
    if existing.data:
        logger.info("Credit pack déjà enregistré pour session %s", stripe_session_id)
        return {"already_processed": True, "pack_id": existing.data["id"]}

    pack = admin.table("credit_packs").insert({
        "organization_id": organization_id,
        "stripe_session_id": stripe_session_id,
        "stripe_payment_intent_id": stripe_payment_intent_id,
        "tokens_granted": tokens,
        "price_chf_paid": price_chf,
        "tokens_remaining": tokens,
    }).execute()

    org = admin.table("organizations").select("tokens_pack_remaining").eq(
        "id", organization_id,
    ).maybe_single().execute()
    current_pack = int(org.data.get("tokens_pack_remaining") or 0) if org.data else 0

    admin.table("organizations").update({
        "tokens_pack_remaining": current_pack + tokens,
    }).eq("id", organization_id).execute()

    logger.info(
        "Credit pack ajouté : org=%s +%d tokens (total pack=%d)",
        organization_id, tokens, current_pack + tokens,
    )

    return {
        "pack_id": pack.data[0]["id"] if pack.data else None,
        "tokens_added": tokens,
        "new_total_pack": current_pack + tokens,
    }
