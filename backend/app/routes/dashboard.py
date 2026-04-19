"""Routes dashboard - KPIs, graphiques, alertes."""
import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends

from app.database import get_supabase_admin
from app.middleware import AuthUser, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def overview(user: Annotated[AuthUser, Depends(get_current_user)]):
    """KPIs principaux du dashboard."""
    admin = get_supabase_admin()
    org_id = user.organization_id

    # Compteurs
    projects = admin.table("projects").select("id", count="exact").eq("organization_id", org_id).eq("status", "active").execute()
    documents = admin.table("documents").select("id", count="exact").eq("organization_id", org_id).execute()
    tasks_total = admin.table("tasks").select("id", count="exact").eq("organization_id", org_id).execute()
    tasks_month = admin.table("tasks").select("id, cost_euros", count="exact").eq("organization_id", org_id).gte(
        "created_at", (datetime.utcnow() - timedelta(days=30)).isoformat()
    ).execute()

    org = admin.table("organizations").select("plan, tasks_used_this_month, tasks_limit").eq("id", org_id).maybe_single().execute()

    # Coût total du mois
    cost_this_month = sum((t.get("cost_euros") or 0) for t in (tasks_month.data or []))

    # Dernières tâches
    recent = admin.table("tasks").select("id, task_type, status, result_preview, created_at").eq("organization_id", org_id).order("created_at", desc=True).limit(10).execute()

    # Alertes réglementaires récentes non traitées
    alerts = admin.table("regulatory_alerts").select("*").eq("processed", False).order("published_at", desc=True).limit(5).execute()

    return {
        "counts": {
            "projects": projects.count or 0,
            "documents": documents.count or 0,
            "tasks_total": tasks_total.count or 0,
            "tasks_month": tasks_month.count or 0,
        },
        "plan": org.data.get("plan") if org.data else "starter",
        "quota": {
            "used": org.data.get("tasks_used_this_month", 0) if org.data else 0,
            "limit": org.data.get("tasks_limit", 500) if org.data else 500,
        },
        "cost_this_month_eur": round(cost_this_month, 2),
        "recent_tasks": recent.data or [],
        "alerts": alerts.data or [],
    }


@router.get("/consumption")
async def consumption_chart(
    user: Annotated[AuthUser, Depends(get_current_user)],
    days: int = 30,
):
    """Données pour graphique de consommation (tâches par jour)."""
    admin = get_supabase_admin()
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()

    tasks = admin.table("tasks").select("created_at, cost_euros, task_type, model_used, status").eq(
        "organization_id", user.organization_id
    ).gte("created_at", since).execute()

    # Agrégation par jour
    by_day: dict[str, dict] = {}
    for t in tasks.data or []:
        day = t["created_at"][:10]
        if day not in by_day:
            by_day[day] = {"date": day, "count": 0, "cost": 0, "completed": 0, "failed": 0}
        by_day[day]["count"] += 1
        by_day[day]["cost"] += (t.get("cost_euros") or 0)
        if t["status"] == "completed":
            by_day[day]["completed"] += 1
        elif t["status"] == "failed":
            by_day[day]["failed"] += 1

    # Ajout jours sans activité
    current = datetime.utcnow().date() - timedelta(days=days - 1)
    end = datetime.utcnow().date()
    while current <= end:
        key = current.isoformat()
        if key not in by_day:
            by_day[key] = {"date": key, "count": 0, "cost": 0, "completed": 0, "failed": 0}
        current += timedelta(days=1)

    series = sorted(by_day.values(), key=lambda x: x["date"])
    for s in series:
        s["cost"] = round(s["cost"], 2)

    # Breakdown par model_used
    by_model: dict[str, int] = {}
    for t in tasks.data or []:
        m = t.get("model_used") or "inconnu"
        by_model[m] = by_model.get(m, 0) + 1

    return {
        "daily": series,
        "by_model": [{"model": k, "count": v} for k, v in by_model.items()],
    }


@router.get("/alerts")
async def alerts(user: Annotated[AuthUser, Depends(get_current_user)], limit: int = 20):
    admin = get_supabase_admin()
    result = admin.table("regulatory_alerts").select("*").order("published_at", desc=True).limit(limit).execute()
    return {"alerts": result.data or []}
