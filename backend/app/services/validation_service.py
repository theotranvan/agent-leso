"""Service de validation assistée des tâches.

Gère les leviers 3 et 4 du plan de réduction du goulot de validation :

  Levier 3 — Approbation 1-clic
    - approve_task() / reject_task() : transition de review_status
    - generate_approval_token() : lien d'approbation par email/mobile
    - approve_via_token() : approbation sans connexion (lien email)

  Levier 4 — Délégation junior
    - can_user_validate() : un utilisateur peut-il valider cette tâche ?
    - apply_auto_delegation() : auto-approbation des tâches éligibles

Règle de sécurité fondamentale
==============================
Les tâches qui engagent la responsabilité professionnelle de l'ingénieur
(note de calcul structure, justificatif thermique, dossier de mise à l'enquête)
sont TOUJOURS réservées à l'ingénieur responsable, quel que soit le score de
confiance. La délégation et l'auto-approbation ne s'appliquent jamais à ces
tâches. C'est un garde-fou non contournable.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from app.database import get_supabase_admin

logger = logging.getLogger(__name__)


# Tâches engageant la responsabilité pro — jamais déléguables ni auto-approuvables
# (doit rester aligné avec QUOTA_PLANS Opus du router et delegation_reserved_tasks)
RESPONSIBILITY_TASKS = frozenset({
    "note_calcul_sia_260_267",
    "justificatif_sia_380_1",
    "dossier_mise_enquete",
    "verification_eurocode",
})

APPROVAL_TOKEN_TTL_HOURS = 72


# ==========================================================================
# LEVIER 4 — DÉLÉGATION
# ==========================================================================

def _get_org_delegation_settings(organization_id: str) -> dict[str, Any]:
    admin = get_supabase_admin()
    org = (
        admin.table("organizations")
        .select(
            "delegation_enabled, delegation_min_confidence, "
            "delegation_reserved_tasks, auto_approve_high_confidence"
        )
        .eq("id", organization_id)
        .maybe_single()
        .execute()
    )
    data = org.data or {}
    return {
        "delegation_enabled": bool(data.get("delegation_enabled", False)),
        "min_confidence": int(data.get("delegation_min_confidence", 85)),
        "reserved_tasks": set(
            data.get("delegation_reserved_tasks")
            or list(RESPONSIBILITY_TASKS)
        ),
        "auto_approve": bool(data.get("auto_approve_high_confidence", False)),
    }


def is_task_reserved(task_type: str, organization_id: str | None = None) -> bool:
    """Une tâche réservée ne peut être validée que par l'ingénieur responsable."""
    if task_type in RESPONSIBILITY_TASKS:
        return True
    if organization_id:
        settings = _get_org_delegation_settings(organization_id)
        return task_type in settings["reserved_tasks"]
    return False


def can_user_validate(
    *,
    user_id: str,
    organization_id: str,
    role: str,
    task: dict[str, Any],
) -> tuple[bool, str]:
    """Détermine si un utilisateur peut valider une tâche donnée.

    Returns (autorisé, raison). La raison explique le refus le cas échéant.
    """
    admin = get_supabase_admin()
    task_type = task.get("task_type", "")
    confidence = task.get("confidence_score") or 0

    # Récupère les flags de l'utilisateur
    u = (
        admin.table("users")
        .select("can_validate, is_engineer_responsible")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    udata = u.data or {}
    is_responsible = bool(udata.get("is_engineer_responsible")) or role == "admin"
    can_validate = bool(udata.get("can_validate")) or is_responsible

    if not can_validate:
        return False, "L'utilisateur n'a pas le droit de valider des documents."

    # L'ingénieur responsable peut tout valider
    if is_responsible:
        return True, "Ingénieur responsable — validation autorisée."

    # Junior validateur : seulement si délégation activée + tâche non réservée + score suffisant
    settings = _get_org_delegation_settings(organization_id)
    if not settings["delegation_enabled"]:
        return False, "La délégation n'est pas activée pour cette organisation."

    if task_type in settings["reserved_tasks"] or task_type in RESPONSIBILITY_TASKS:
        return False, (
            "Cette tâche engage la responsabilité professionnelle et est réservée "
            "à l'ingénieur responsable."
        )

    if confidence < settings["min_confidence"]:
        return False, (
            f"Score de confiance {confidence}% < seuil de délégation "
            f"{settings['min_confidence']}% — validation par le responsable requise."
        )

    return True, "Délégation autorisée (tâche non réservée, confiance suffisante)."


def apply_auto_delegation(task_id: str) -> dict[str, Any]:
    """Auto-approuve une tâche si l'organisation l'autorise et que la tâche est éligible.

    Appelé après le calcul de confiance. Ne touche jamais aux tâches réservées.
    """
    admin = get_supabase_admin()
    task = (
        admin.table("tasks")
        .select("id, organization_id, task_type, confidence_score, confidence_level, review_status")
        .eq("id", task_id)
        .maybe_single()
        .execute()
    )
    if not task.data:
        return {"auto_approved": False, "reason": "Tâche introuvable"}

    t = task.data
    task_type = t.get("task_type", "")
    settings = _get_org_delegation_settings(t["organization_id"])

    if not settings["auto_approve"]:
        return {"auto_approved": False, "reason": "Auto-approbation désactivée"}

    if task_type in settings["reserved_tasks"] or task_type in RESPONSIBILITY_TASKS:
        return {"auto_approved": False, "reason": "Tâche réservée au responsable"}

    if t.get("confidence_level") != "high":
        return {"auto_approved": False, "reason": "Confiance non haute"}

    if (t.get("confidence_score") or 0) < settings["min_confidence"]:
        return {"auto_approved": False, "reason": "Score sous le seuil"}

    # Éligible → auto-approbation
    admin.table("tasks").update({
        "review_status": "approved",
        "approved_at": datetime.utcnow().isoformat(),
        "approval_channel": "auto_delegated",
        "approval_note": "Auto-approuvée (confiance haute, tâche non réservée).",
    }).eq("id", task_id).execute()

    logger.info("Task %s auto-approuvée (délégation org)", task_id)
    return {"auto_approved": True, "reason": "Confiance haute + tâche éligible"}


# ==========================================================================
# LEVIER 3 — APPROBATION 1-CLIC
# ==========================================================================

def approve_task(
    *,
    task_id: str,
    user_id: str,
    organization_id: str,
    role: str,
    note: str = "",
    channel: str = "web",
) -> dict[str, Any]:
    """Approuve une tâche après vérification des droits."""
    admin = get_supabase_admin()
    task = (
        admin.table("tasks")
        .select("*")
        .eq("id", task_id)
        .eq("organization_id", organization_id)
        .maybe_single()
        .execute()
    )
    if not task.data:
        raise ValueError("Tâche introuvable")

    allowed, reason = can_user_validate(
        user_id=user_id, organization_id=organization_id, role=role, task=task.data,
    )
    if not allowed:
        raise PermissionError(reason)

    admin.table("tasks").update({
        "review_status": "approved",
        "approved_by": user_id,
        "approved_at": datetime.utcnow().isoformat(),
        "approval_note": note,
        "approval_channel": channel,
    }).eq("id", task_id).execute()

    admin.table("audit_logs").insert({
        "organization_id": organization_id,
        "user_id": user_id,
        "action": "task_approved",
        "resource_type": "task",
        "resource_id": task_id,
        "metadata": {"channel": channel, "confidence": task.data.get("confidence_score")},
    }).execute()

    logger.info("Task %s approuvée par user=%s via %s", task_id, user_id, channel)
    return {"task_id": task_id, "review_status": "approved", "reason": reason}


def reject_task(
    *,
    task_id: str,
    user_id: str,
    organization_id: str,
    role: str,
    note: str = "",
    channel: str = "web",
) -> dict[str, Any]:
    """Rejette une tâche (à régénérer)."""
    admin = get_supabase_admin()
    task = (
        admin.table("tasks")
        .select("*")
        .eq("id", task_id)
        .eq("organization_id", organization_id)
        .maybe_single()
        .execute()
    )
    if not task.data:
        raise ValueError("Tâche introuvable")

    allowed, reason = can_user_validate(
        user_id=user_id, organization_id=organization_id, role=role, task=task.data,
    )
    if not allowed:
        raise PermissionError(reason)

    admin.table("tasks").update({
        "review_status": "rejected",
        "approved_by": user_id,
        "approved_at": datetime.utcnow().isoformat(),
        "approval_note": note,
        "approval_channel": channel,
    }).eq("id", task_id).execute()

    admin.table("audit_logs").insert({
        "organization_id": organization_id,
        "user_id": user_id,
        "action": "task_rejected",
        "resource_type": "task",
        "resource_id": task_id,
        "metadata": {"channel": channel, "note": note[:200]},
    }).execute()

    return {"task_id": task_id, "review_status": "rejected", "reason": reason}


# ---- Tokens d'approbation pour les liens email / mobile ----

def generate_approval_token(
    *,
    task_id: str,
    organization_id: str,
    user_id: str | None = None,
    action: str = "approve",
) -> str:
    """Génère un token d'approbation à usage unique pour un lien email.

    Retourne le token EN CLAIR (à mettre dans l'URL). Seul son hash est stocké.
    """
    admin = get_supabase_admin()
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires = datetime.utcnow() + timedelta(hours=APPROVAL_TOKEN_TTL_HOURS)

    admin.table("approval_tokens").insert({
        "task_id": task_id,
        "organization_id": organization_id,
        "token_hash": token_hash,
        "action": action,
        "created_for_user": user_id,
        "expires_at": expires.isoformat(),
    }).execute()

    return raw_token


def approve_via_token(raw_token: str) -> dict[str, Any]:
    """Approuve (ou rejette) une tâche via un token de lien email, sans connexion.

    Vérifie : token existe, non utilisé, non expiré. Marque utilisé après usage.
    """
    admin = get_supabase_admin()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    tok = (
        admin.table("approval_tokens")
        .select("*")
        .eq("token_hash", token_hash)
        .maybe_single()
        .execute()
    )
    if not tok.data:
        raise ValueError("Lien d'approbation invalide.")

    t = tok.data
    if t.get("used_at"):
        raise ValueError("Ce lien d'approbation a déjà été utilisé.")

    expires = datetime.fromisoformat(t["expires_at"].replace("Z", "+00:00"))
    if datetime.now(expires.tzinfo) > expires:
        raise ValueError("Ce lien d'approbation a expiré.")

    new_status = "approved" if t["action"] == "approve" else "rejected"
    admin.table("tasks").update({
        "review_status": new_status,
        "approved_by": t.get("created_for_user"),
        "approved_at": datetime.utcnow().isoformat(),
        "approval_channel": "email",
        "approval_note": "Approbation via lien email.",
    }).eq("id", t["task_id"]).execute()

    # Marque le token utilisé
    admin.table("approval_tokens").update({
        "used_at": datetime.utcnow().isoformat(),
    }).eq("id", t["id"]).execute()

    admin.table("audit_logs").insert({
        "organization_id": t["organization_id"],
        "user_id": t.get("created_for_user"),
        "action": f"task_{new_status}",
        "resource_type": "task",
        "resource_id": t["task_id"],
        "metadata": {"channel": "email_token"},
    }).execute()

    return {"task_id": t["task_id"], "review_status": new_status}


# ==========================================================================
# LEVIER 2 — ALERTES CIBLÉES (extraction depuis le score)
# ==========================================================================

def get_review_alerts(task: dict[str, Any]) -> dict[str, Any]:
    """Retourne uniquement les points à vérifier d'une tâche (Levier 2).

    Au lieu de demander à l'ingénieur de relire tout le document, on lui
    présente seulement les alertes ciblées + le score.
    """
    alerts = task.get("confidence_alerts") or []
    detail = task.get("confidence_detail") or {}
    failed_checks = [
        c for c in detail.get("checks", [])
        if not c.get("passed") and c.get("is_alert")
    ]

    return {
        "task_id": task.get("id"),
        "confidence_score": task.get("confidence_score"),
        "confidence_level": task.get("confidence_level"),
        "ready_to_approve": task.get("confidence_level") == "high",
        "alerts": alerts,
        "failed_checks": failed_checks,
        "summary": detail.get("summary", ""),
        "nb_points_to_verify": len(alerts),
    }
