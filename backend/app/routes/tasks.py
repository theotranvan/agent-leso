"""Routes tâches - création, suivi temps réel, liste."""
import logging
from typing import Annotated, Optional

from arq.connections import RedisSettings, create_pool
from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.database import get_supabase_admin
from app.middleware import AuthUser, audit_log, check_quota, get_current_user
from app.models.task import TaskCreate, TaskStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _get_redis_pool():
    """Pool ARQ pour publier des jobs."""
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))


@router.post("", status_code=202)
async def create_task(
    body: TaskCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    """Crée une tâche et la pousse dans la queue ARQ."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    await check_quota(user)

    admin = get_supabase_admin()
    input_params = dict(body.input_params or {})
    input_params["send_email"] = body.send_email
    input_params["recipient_emails"] = body.recipient_emails

    result = admin.table("tasks").insert({
        "organization_id": user.organization_id,
        "project_id": body.project_id,
        "user_id": user.id,
        "task_type": body.task_type,
        "status": "pending",
        "input_params": input_params,
    }).execute()
    task = result.data[0]

    # Publie dans ARQ
    try:
        pool = await _get_redis_pool()
        await pool.enqueue_job("run_task", task["id"])
    except Exception as e:
        logger.error(f"Erreur publication ARQ: {e}")
        admin.table("tasks").update({"status": "failed", "error_message": f"Queue indisponible: {e}"}).eq("id", task["id"]).execute()
        raise HTTPException(status_code=503, detail="Queue indisponible, réessayez plus tard")

    await audit_log(
        action="task_created",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="task",
        resource_id=task["id"],
        metadata={"task_type": body.task_type},
        ip_address=request.client.host if request.client else None,
    )

    return task


@router.get("")
async def list_tasks(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    admin = get_supabase_admin()
    query = admin.table("tasks").select("*").eq("organization_id", user.organization_id)
    if project_id:
        query = query.eq("project_id", project_id)
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return {"tasks": result.data or []}


@router.get("/{task_id}")
async def get_task(task_id: str, user: Annotated[AuthUser, Depends(get_current_user)]):
    admin = get_supabase_admin()
    task = admin.table("tasks").select("*").eq("id", task_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not task.data:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return task.data


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, user: Annotated[AuthUser, Depends(get_current_user)]):
    """Endpoint léger de polling pour le frontend (toutes les 3s)."""
    admin = get_supabase_admin()
    task = admin.table("tasks").select("id, status, result_url, result_preview, error_message, created_at, completed_at").eq("id", task_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not task.data:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    status_to_progress = {"pending": 5, "running": 50, "completed": 100, "failed": 0}
    return TaskStatusResponse(
        id=task.data["id"],
        status=task.data["status"],
        progress=status_to_progress.get(task.data["status"], 0),
        result_url=task.data.get("result_url"),
        result_preview=task.data.get("result_preview"),
        error_message=task.data.get("error_message"),
    )


@router.post("/{task_id}/retry", status_code=202)
async def retry_task(
    task_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    """Relance une tâche en échec."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    task = admin.table("tasks").select("*").eq("id", task_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not task.data:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    if task.data["status"] not in ("failed", "completed"):
        raise HTTPException(status_code=400, detail="La tâche n'est pas en état d'être relancée")

    admin.table("tasks").update({"status": "pending", "error_message": None}).eq("id", task_id).execute()

    pool = await _get_redis_pool()
    await pool.enqueue_job("run_task", task_id)

    await audit_log(
        action="task_retried",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="task",
        resource_id=task_id,
        ip_address=request.client.host if request.client else None,
    )
    return {"status": "retried", "task_id": task_id}
