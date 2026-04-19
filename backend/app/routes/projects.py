"""Routes CRUD projets."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user
from app.models.project import Project, ProjectCreate, ProjectUpdate

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
