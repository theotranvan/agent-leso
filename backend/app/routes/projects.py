"""Routes CRUD projets."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user
from app.models.project import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects(user: Annotated[AuthUser, Depends(get_current_user)], archived: bool = False):
    admin = get_supabase_admin()
    status = "archived" if archived else "active"
    result = admin.table("projects").select("*").eq("organization_id", user.organization_id).eq("status", status).order("created_at", desc=True).execute()
    return {"projects": result.data or []}


@router.post("", status_code=201)
async def create_project(
    body: ProjectCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    result = admin.table("projects").insert({
        **body.model_dump(),
        "organization_id": user.organization_id,
    }).execute()

    project = result.data[0]
    await audit_log(
        action="project_created",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="project",
        resource_id=project["id"],
        ip_address=request.client.host if request.client else None,
    )
    return project


@router.get("/{project_id}")
async def get_project(project_id: str, user: Annotated[AuthUser, Depends(get_current_user)]):
    admin = get_supabase_admin()
    project = admin.table("projects").select("*").eq("id", project_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not project.data:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    # Compteurs associés
    docs = admin.table("documents").select("id", count="exact").eq("project_id", project_id).execute()
    tasks = admin.table("tasks").select("id", count="exact").eq("project_id", project_id).execute()

    return {
        **project.data,
        "nb_documents": docs.count or 0,
        "nb_tasks": tasks.count or 0,
    }


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    payload = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    from datetime import datetime
    payload["updated_at"] = datetime.utcnow().isoformat()

    result = admin.table("projects").update(payload).eq("id", project_id).eq("organization_id", user.organization_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    return result.data[0]


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Droits admin requis")

    admin = get_supabase_admin()
    result = admin.table("projects").delete().eq("id", project_id).eq("organization_id", user.organization_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    await audit_log(
        action="project_deleted",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="project",
        resource_id=project_id,
        ip_address=request.client.host if request.client else None,
    )
    return None


@router.get("/{project_id}/documents")
async def list_project_documents(project_id: str, user: Annotated[AuthUser, Depends(get_current_user)]):
    admin = get_supabase_admin()
    docs = admin.table("documents").select("*").eq("project_id", project_id).eq("organization_id", user.organization_id).order("created_at", desc=True).execute()
    return {"documents": docs.data or []}


@router.get("/{project_id}/tasks")
async def list_project_tasks(project_id: str, user: Annotated[AuthUser, Depends(get_current_user)], limit: int = 50):
    admin = get_supabase_admin()
    tasks = admin.table("tasks").select("*").eq("project_id", project_id).eq("organization_id", user.organization_id).order("created_at", desc=True).limit(limit).execute()
    return {"tasks": tasks.data or []}


@router.get("/{project_id}/journey")
async def get_project_journey(project_id: str, user: Annotated[AuthUser, Depends(get_current_user)]):
    """Parcours d'affaire : état d'avancement par phase SIA + action recommandée.

    Guide l'ingénieur à travers le cycle de vie du projet. Indicatif, non bloquant.
    """
    from app.agent.project_journey import compute_journey_state

    admin = get_supabase_admin()
    project = (
        admin.table("projects").select("*")
        .eq("id", project_id).eq("organization_id", user.organization_id)
        .maybe_single().execute()
    )
    if not project.data:
        raise HTTPException(status_code=404, detail="Projet introuvable")

    # Récupère les tâches du projet pour calculer l'avancement
    tasks = (
        admin.table("tasks")
        .select("task_type, status, review_status")
        .eq("project_id", project_id)
        .eq("organization_id", user.organization_id)
        .execute()
    )
    rows = tasks.data or []
    completed = [t["task_type"] for t in rows if t.get("status") == "completed"]
    approved = [t["task_type"] for t in rows if t.get("review_status") == "approved"]

    # "Création de l'affaire" (project_setup) n'est pas une tâche agent : on la
    # considère faite dès que les données de base du projet sont renseignées.
    pdata = project.data
    if pdata.get("canton") and pdata.get("affectation"):
        completed.append("project_setup")
        approved.append("project_setup")

    # Phases désactivées au niveau organisation (modularité)
    org = (
        admin.table("organizations").select("disabled_journey_phases")
        .eq("id", user.organization_id).maybe_single().execute()
    )
    disabled = (org.data or {}).get("disabled_journey_phases") or []

    state = compute_journey_state(
        completed_task_types=completed,
        approved_task_types=approved,
        current_phase=project.data.get("current_phase"),
        disabled_phases=disabled,
        canton=project.data.get("canton"),
    )
    return state


@router.patch("/{project_id}/phase")
async def set_project_phase(
    project_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    body: dict,
):
    """Déclare manuellement la phase courante d'un projet (l'ingénieur garde la main)."""
    from app.agent.project_journey import PHASE_BY_KEY

    phase = body.get("current_phase")
    if phase and phase not in PHASE_BY_KEY:
        raise HTTPException(status_code=400, detail="Phase inconnue")

    admin = get_supabase_admin()
    result = (
        admin.table("projects").update({"current_phase": phase})
        .eq("id", project_id).eq("organization_id", user.organization_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    return {"project_id": project_id, "current_phase": phase}


@router.get("/{project_id}/export-dossier")
async def export_dossier(
    project_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    only_approved: bool = True,
):
    """Export dossier AO complet en ZIP (point 5)."""
    import io

    from fastapi.responses import StreamingResponse

    from app.services.ao_export import build_ao_dossier_zip

    try:
        zip_bytes, filename, summary = await build_ao_dossier_zip(
            project_id, user.organization_id, only_approved=only_approved,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if summary["documents_included"] == 0:
        raise HTTPException(
            status_code=400,
            detail="Aucun document à exporter. "
                   + ("Validez d'abord des documents." if only_approved else ""),
        )

    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{project_id}/deadlines")
async def list_deadlines(project_id: str, user: Annotated[AuthUser, Depends(get_current_user)]):
    """Liste les échéances d'un projet."""
    admin = get_supabase_admin()
    rows = (
        admin.table("project_deadlines").select("*")
        .eq("project_id", project_id).eq("organization_id", user.organization_id)
        .order("due_date").execute()
    )
    return {"deadlines": rows.data or []}


@router.post("/{project_id}/deadlines", status_code=201)
async def create_deadline(
    project_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    body: dict,
):
    """Ajoute une échéance (ex: dépôt AEAI, permis de construire)."""
    from app.services.calendar_export import add_deadline
    if not body.get("label") or not body.get("due_date"):
        raise HTTPException(status_code=400, detail="label et due_date requis")
    return add_deadline(
        organization_id=user.organization_id, project_id=project_id,
        label=body["label"], due_date=body["due_date"],
        phase_key=body.get("phase_key"),
    )


@router.get("/{project_id}/calendar.ics")
async def project_calendar(project_id: str, user: Annotated[AuthUser, Depends(get_current_user)]):
    """Export .ics des échéances d'un projet (Google Calendar / Outlook / Apple)."""
    from fastapi.responses import Response

    from app.services.calendar_export import build_ics_for_project
    ics = build_ics_for_project(project_id, user.organization_id)
    return Response(
        content=ics, media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="echeances.ics"'},
    )
