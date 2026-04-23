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


@router.get("/compliance")
async def compliance_overview(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Tableau de bord conformité multi-projets.

    Retourne pour chaque projet :
      - Statut IDC (dernier calcul)
      - Conformité thermique (dernier justificatif)
      - Validation structure (dernier calcul validé par ingénieur)
      - Nombre checklists AEAI validées
      - Dossier d'enquête : couverture pièces
      - Observations autorité ouvertes
      - Deadline la plus proche
      - Dernière activité
    """
    admin = get_supabase_admin()

    # Tentative via la VIEW SQL si migration 004 appliquée
    try:
        view_result = admin.table("project_compliance_dashboard").select("*").eq(
            "organization_id", user.organization_id,
        ).execute()
        if view_result.data is not None:
            return {"projects": view_result.data or []}
    except Exception:
        pass  # VIEW pas encore déployée → fallback agrégation manuelle

    # Fallback : agrégation côté applicatif
    projects_r = admin.table("projects").select("*").eq(
        "organization_id", user.organization_id,
    ).order("created_at", desc=True).execute()
    projects = projects_r.data or []

    if not projects:
        return {"projects": []}

    project_ids = [p["id"] for p in projects]

    # Tâches récentes par projet
    tasks_r = admin.table("tasks").select(
        "id, project_id, task_type, status, completed_at, created_at, result_preview"
    ).in_("project_id", project_ids).order("created_at", desc=True).limit(500).execute()
    tasks_by_project: dict[str, list[dict]] = {}
    for t in tasks_r.data or []:
        pid = t.get("project_id")
        if pid:
            tasks_by_project.setdefault(pid, []).append(t)

    # Checklists AEAI
    aeai_r = admin.table("aeai_checklists").select(
        "project_id, status, updated_at"
    ).in_("project_id", project_ids).execute()
    aeai_by_project: dict[str, dict] = {}
    for c in aeai_r.data or []:
        pid = c.get("project_id")
        if pid:
            current = aeai_by_project.get(pid, {"total": 0, "validated": 0, "last_update": None})
            current["total"] += 1
            if c.get("status") in ("validated", "ready"):
                current["validated"] += 1
            if c.get("updated_at"):
                current["last_update"] = max(
                    current.get("last_update") or "",
                    c["updated_at"],
                )
            aeai_by_project[pid] = current

    def _latest_task_of_type(pid: str, types: tuple[str, ...]) -> dict | None:
        for t in tasks_by_project.get(pid, []):
            if t["task_type"] in types:
                return t
        return None

    out: list[dict] = []
    for p in projects:
        pid = p["id"]
        project_tasks = tasks_by_project.get(pid, [])

        idc_task = _latest_task_of_type(pid, ("idc_geneve_rapport",))
        thermique_task = _latest_task_of_type(pid, ("justificatif_sia_380_1", "simulation_energetique_rapide"))
        structure_task = _latest_task_of_type(pid, ("note_calcul_sia_260_267",))
        dossier_task = _latest_task_of_type(pid, ("dossier_mise_enquete",))
        obs_tasks = [t for t in project_tasks if t["task_type"] == "reponse_observations_autorite"]

        aeai_info = aeai_by_project.get(pid, {"total": 0, "validated": 0, "last_update": None})

        last_activity = None
        if project_tasks:
            last_activity = project_tasks[0].get("completed_at") or project_tasks[0].get("created_at")

        out.append({
            "project_id": pid,
            "project_name": p.get("name"),
            "canton": p.get("canton"),
            "phase_sia": p.get("phase_sia"),
            "affectation": p.get("affectation"),
            "sre_m2": p.get("sre_m2"),
            "idc": {
                "status": idc_task["status"] if idc_task else "non_calcule",
                "last_date": idc_task.get("completed_at") if idc_task else None,
                "preview": idc_task.get("result_preview") if idc_task else None,
            },
            "thermique": {
                "status": thermique_task["status"] if thermique_task else "non_calcule",
                "last_date": thermique_task.get("completed_at") if thermique_task else None,
            },
            "structure": {
                "status": structure_task["status"] if structure_task else "non_calcule",
                "last_date": structure_task.get("completed_at") if structure_task else None,
            },
            "aeai": {
                "nb_checklists": aeai_info["total"],
                "nb_validated": aeai_info["validated"],
                "last_update": aeai_info["last_update"],
            },
            "dossier_enquete": {
                "status": dossier_task["status"] if dossier_task else "non_commence",
                "last_date": dossier_task.get("completed_at") if dossier_task else None,
            },
            "observations": {
                "nb_total": len(obs_tasks),
                "nb_pending": sum(1 for t in obs_tasks if t["status"] in ("queued", "running")),
            },
            "last_activity_at": last_activity,
            "created_at": p.get("created_at"),
        })

    # Tri par dernière activité décroissante
    out.sort(key=lambda x: x.get("last_activity_at") or x.get("created_at") or "", reverse=True)

    return {"projects": out}
