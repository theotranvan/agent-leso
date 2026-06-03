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

    projects = admin.table("projects").select("id", count="exact").eq("organization_id", org_id).eq("status", "active").execute()
    tasks_total = admin.table("tasks").select("id", count="exact").eq("organization_id", org_id).execute()
    tasks_running = admin.table("tasks").select("id", count="exact").eq("organization_id", org_id).in_("status", ["pending", "running"]).execute()
    tasks_month = admin.table("tasks").select("id, cost_euros", count="exact").eq("organization_id", org_id).gte(
        "created_at", (datetime.utcnow() - timedelta(days=30)).isoformat()
    ).execute()

    org = admin.table("organizations").select("plan, tasks_used_this_month, tasks_limit").eq("id", org_id).maybe_single().execute()
    plan = (org.data.get("plan") if org.data else None) or "starter"

    cost_this_month = sum((t.get("cost_euros") or 0) for t in (tasks_month.data or []))

    recent = admin.table("tasks").select("id, task_type, status, result_url, result_preview, created_at").eq("organization_id", org_id).order("created_at", desc=True).limit(10).execute()

    recent_projects_res = admin.table("projects").select("id, name, canton, affectation").eq("organization_id", org_id).order("updated_at", desc=True).limit(5).execute()

    alerts = admin.table("regulatory_alerts").select("id, title, published_at, source").eq("processed", False).order("published_at", desc=True).limit(5).execute()

    return {
        "stats": {
            "projects_count": projects.count or 0,
            "tasks_total": tasks_total.count or 0,
            "running_tasks": tasks_running.count or 0,
            "tasks_month": tasks_month.count or 0,
        },
        "quota": {
            "used": org.data.get("tasks_used_this_month", 0) if org.data else 0,
            "limit": org.data.get("tasks_limit", 500) if org.data else 500,
            "plan": plan,
        },
        "cost_this_month_eur": round(cost_this_month, 2),
        "recent_tasks": recent.data or [],
        "recent_projects": recent_projects_res.data or [],
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


@router.get("/engineer")
async def engineer_dashboard(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Dashboard ingénieur (point 3) : vue orientée action quotidienne.

    Ce que l'ingénieur veut voir en ouvrant l'app : affaires de la semaine,
    documents à valider, échéances proches, consommation, prochaines actions.
    """
    from app.services.notification_service import build_notifications

    admin = get_supabase_admin()
    org_id = user.organization_id
    now = datetime.utcnow()
    week_ago = (now - timedelta(days=7)).isoformat()

    # Affaires actives
    projects = (
        admin.table("projects").select("id, name, current_phase, status")
        .eq("organization_id", org_id).eq("status", "active").execute()
    )
    active_projects = projects.data or []

    # Tâches de la semaine
    tasks_week = (
        admin.table("tasks").select("id, task_type, status, created_at, review_status")
        .eq("organization_id", org_id).gte("created_at", week_ago).execute()
    )
    tw = tasks_week.data or []

    # File de validation
    to_validate = [
        t for t in tw
        if t.get("status") == "completed"
        and t.get("review_status") in ("pending_review", "ready_to_approve", "needs_revision")
    ]

    # Notifications proactives
    notifications = build_notifications(org_id)

    # Consommation tokens du mois — select("*") + limit(1) pour éviter le crash
    # PostgREST "Missing response 204" si une colonne de quota manque en base.
    org = (
        admin.table("organizations")
        .select("*").eq("id", org_id).limit(1).execute()
    )
    odata = (org.data or [{}])[0]
    # tolère les deux conventions de nommage présentes dans la base
    tokens_used = (
        odata.get("tokens_used_this_month")
        or odata.get("tokens_used_current_month")
        or 0
    )
    tokens_quota = (
        odata.get("token_quota_monthly")
        or odata.get("tokens_limit_monthly")
        or 0
    )

    return {
        "kpis": {
            "active_projects": len(active_projects),
            "tasks_this_week": len(tw),
            "to_validate": len(to_validate),
            "tokens_used": tokens_used,
            "tokens_quota": tokens_quota,
            "tokens_pct": round(tokens_used / tokens_quota * 100) if tokens_quota else 0,
            "plan": odata.get("plan", "starter"),
        },
        "to_validate": to_validate[:8],
        "active_projects": active_projects[:8],
        "notifications": notifications,
    }


@router.get("/analytics")
async def analytics_dashboard(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Analytics BET (point 6) : temps économisé, taux d'approbation, types fréquents."""
    admin = get_supabase_admin()
    org_id = user.organization_id
    month_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()

    tasks = (
        admin.table("tasks").select("task_type, status, review_status, confidence_score")
        .eq("organization_id", org_id).gte("created_at", month_ago).execute()
    )
    rows = tasks.data or []
    completed = [t for t in rows if t.get("status") == "completed"]

    # Estimation du temps économisé (jours-ingénieur par type de tâche)
    TIME_SAVED_DAYS = {
        "redaction_cctp": 7.5, "justificatif_sia_380_1": 2.5,
        "note_calcul_sia_260_267": 4.0, "chiffrage_dpgf": 2.75,
        "coordination_inter_lots": 1.5, "aeai_checklist_generation": 0.6,
        "idc_geneve_rapport": 0.65, "dossier_mise_enquete": 2.0,
        "doe_compilation": 1.5, "simulation_energetique_rapide": 0.5,
        "controle_reglementaire_vaud": 0.8, "metres_automatiques_ifc": 1.0,
    }
    days_saved = sum(TIME_SAVED_DAYS.get(t["task_type"], 0.3) for t in completed)
    chf_saved = round(days_saved * 850)  # taux ingénieur moyen Suisse romande

    # Taux d'approbation directe vs renvoi
    approved = sum(1 for t in completed if t.get("review_status") == "approved")
    rejected = sum(1 for t in completed if t.get("review_status") == "rejected")
    total_reviewed = approved + rejected
    approval_rate = round(approved / total_reviewed * 100) if total_reviewed else 0

    # Types de documents les plus fréquents
    from collections import Counter
    type_counts = Counter(t["task_type"] for t in completed)
    top_types = [{"task_type": k, "count": v} for k, v in type_counts.most_common(6)]

    # Confiance moyenne
    scores = [t["confidence_score"] for t in completed if t.get("confidence_score") is not None]
    avg_confidence = round(sum(scores) / len(scores)) if scores else None

    return {
        "period_days": 30,
        "documents_produced": len(completed),
        "days_saved": round(days_saved, 1),
        "chf_saved": chf_saved,
        "approval_rate": approval_rate,
        "approved": approved,
        "rejected": rejected,
        "avg_confidence": avg_confidence,
        "top_types": top_types,
    }


@router.get("/notifications")
async def get_notifications(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Liste des notifications proactives actives."""
    from app.services.notification_service import build_notifications
    return {"notifications": build_notifications(user.organization_id)}


@router.get("/board")
async def projects_board(user: Annotated[AuthUser, Depends(get_current_user)]):
    """Vue kanban : affaires groupées par phase SIA avec compteurs d'actions.

    Pour le chef de projet : voir toutes ses affaires par phase en un coup d'œil,
    avec le nombre de documents à valider sur chacune.
    """
    from app.agent.project_journey import PROJECT_JOURNEY

    admin = get_supabase_admin()
    org_id = user.organization_id

    projects = (
        admin.table("projects")
        .select("id, name, current_phase, commune, canton, sre_m2, labels, status")
        .eq("organization_id", org_id).eq("status", "active").execute()
    )
    proj_rows = projects.data or []

    # Compteurs de tâches à valider par projet
    tasks = (
        admin.table("tasks")
        .select("project_id, review_status, status")
        .eq("organization_id", org_id).eq("status", "completed").execute()
    )
    to_validate_by_project: dict[str, int] = {}
    for t in tasks.data or []:
        if t.get("review_status") in ("pending_review", "ready_to_approve", "needs_revision"):
            pid = t.get("project_id")
            if pid:
                to_validate_by_project[pid] = to_validate_by_project.get(pid, 0) + 1

    # Échéances proches par projet
    from datetime import date, timedelta
    soon = (date.today() + timedelta(days=14)).isoformat()
    deadlines = (
        admin.table("project_deadlines")
        .select("project_id, label, due_date")
        .eq("organization_id", org_id).eq("completed", False)
        .lte("due_date", soon).execute()
    )
    deadline_by_project: dict[str, dict] = {}
    for d in deadlines.data or []:
        pid = d.get("project_id")
        if pid and pid not in deadline_by_project:
            deadline_by_project[pid] = {"label": d["label"], "due_date": d["due_date"]}

    # Construction des colonnes par phase
    columns = []
    for phase in sorted(PROJECT_JOURNEY, key=lambda x: x.order):
        if phase.key == "initiation":
            continue  # on ne montre pas la colonne "création"
        phase_projects = [
            {
                **p,
                "to_validate": to_validate_by_project.get(p["id"], 0),
                "next_deadline": deadline_by_project.get(p["id"]),
            }
            for p in proj_rows
            if (p.get("current_phase") or "avant_projet") == phase.key
        ]
        columns.append({
            "phase_key": phase.key,
            "sia_code": phase.sia_code,
            "label": phase.label,
            "projects": phase_projects,
            "count": len(phase_projects),
        })

    return {
        "columns": columns,
        "total_projects": len(proj_rows),
        "total_to_validate": sum(to_validate_by_project.values()),
    }
