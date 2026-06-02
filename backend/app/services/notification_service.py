"""Service de notifications proactives.

Génère et expose les notifications intelligentes pour l'ingénieur :
- documents en attente de validation depuis trop longtemps
- échéances réglementaires (AEAI, permis) qui approchent ou dépassées
- quota de tokens proche de la limite
- suggestion de prochaine action dans le parcours

Les notifications sont calculées à la volée (dashboard) et/ou matérialisées
en base pour un suivi (table notifications).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from app.database import get_supabase_admin

logger = logging.getLogger(__name__)

PENDING_VALIDATION_HOURS = 48      # seuil d'alerte pour validation en attente
DEADLINE_WARNING_DAYS = 7          # alerte si échéance dans moins de X jours
QUOTA_WARNING_PCT = 80             # alerte si quota consommé ≥ X%


def build_notifications(organization_id: str) -> list[dict[str, Any]]:
    """Calcule les notifications actives pour une organisation.

    Calcul à la volée — ne crée pas d'entrées en base. Idéal pour le dashboard.
    """
    admin = get_supabase_admin()
    notifications: list[dict[str, Any]] = []
    now = datetime.utcnow()
    today = date.today()

    # ---- 1. Documents en attente de validation depuis > 48h ----
    threshold = (now - timedelta(hours=PENDING_VALIDATION_HOURS)).isoformat()
    pending = (
        admin.table("tasks")
        .select("id, task_type, completed_at, project_id, confidence_score")
        .eq("organization_id", organization_id)
        .eq("status", "completed")
        .in_("review_status", ["pending_review", "ready_to_approve"])
        .lt("completed_at", threshold)
        .limit(20)
        .execute()
    )
    pending_rows = pending.data or []
    if pending_rows:
        notifications.append({
            "type": "pending_validation",
            "severity": "warning",
            "title": f"{len(pending_rows)} document(s) en attente de validation",
            "body": f"Des documents attendent votre validation depuis plus de "
                    f"{PENDING_VALIDATION_HOURS}h.",
            "action_url": "/validation",
            "count": len(pending_rows),
        })

    # ---- 2. Échéances réglementaires ----
    warning_date = (today + timedelta(days=DEADLINE_WARNING_DAYS)).isoformat()
    deadlines = (
        admin.table("project_deadlines")
        .select("id, label, due_date, project_id")
        .eq("organization_id", organization_id)
        .eq("completed", False)
        .lte("due_date", warning_date)
        .order("due_date")
        .limit(20)
        .execute()
    )
    for d in deadlines.data or []:
        try:
            due = date.fromisoformat(d["due_date"])
        except (ValueError, TypeError):
            continue
        days_left = (due - today).days
        if days_left < 0:
            notifications.append({
                "type": "deadline_overdue",
                "severity": "urgent",
                "title": f"Échéance dépassée : {d['label']}",
                "body": f"Cette échéance était fixée au {due.strftime('%d/%m/%Y')} "
                        f"({abs(days_left)} j de retard).",
                "action_url": f"/projects/{d['project_id']}",
                "project_id": d["project_id"],
            })
        else:
            notifications.append({
                "type": "deadline_approaching",
                "severity": "warning" if days_left <= 3 else "info",
                "title": f"Échéance dans {days_left} j : {d['label']}",
                "body": f"À traiter avant le {due.strftime('%d/%m/%Y')}.",
                "action_url": f"/projects/{d['project_id']}",
                "project_id": d["project_id"],
            })

    # ---- 3. Quota tokens ----
    try:
        org = (
            admin.table("organizations")
            .select("tokens_used_this_month, token_quota_monthly, plan")
            .eq("id", organization_id)
            .maybe_single()
            .execute()
        )
        if org.data:
            used = org.data.get("tokens_used_this_month") or 0
            quota = org.data.get("token_quota_monthly") or 0
            if quota > 0:
                pct = round(used / quota * 100)
                if pct >= QUOTA_WARNING_PCT:
                    notifications.append({
                        "type": "quota_warning",
                        "severity": "urgent" if pct >= 95 else "warning",
                        "title": f"Quota de tokens à {pct}%",
                        "body": f"{used:,} / {quota:,} tokens utilisés ce mois. "
                                f"Pensez à un credit pack si nécessaire.",
                        "action_url": "/billing",
                    })
    except Exception as exc:
        logger.warning("Check quota notif échec : %s", exc)

    # Tri par sévérité (urgent en premier)
    sev_order = {"urgent": 0, "warning": 1, "info": 2}
    notifications.sort(key=lambda n: sev_order.get(n["severity"], 3))
    return notifications


def create_notification(
    *,
    organization_id: str,
    type: str,
    title: str,
    body: str = "",
    severity: str = "info",
    user_id: str | None = None,
    project_id: str | None = None,
    task_id: str | None = None,
    action_url: str | None = None,
) -> dict[str, Any]:
    """Matérialise une notification en base (pour suivi persistant)."""
    admin = get_supabase_admin()
    row = {
        "organization_id": organization_id,
        "type": type,
        "severity": severity,
        "title": title,
        "body": body,
        "user_id": user_id,
        "project_id": project_id,
        "task_id": task_id,
        "action_url": action_url,
    }
    result = admin.table("notifications").insert(row).execute()
    return (result.data or [{}])[0]


def mark_read(notification_id: str, organization_id: str) -> None:
    admin = get_supabase_admin()
    admin.table("notifications").update({
        "read_at": datetime.utcnow().isoformat(),
    }).eq("id", notification_id).eq("organization_id", organization_id).execute()
