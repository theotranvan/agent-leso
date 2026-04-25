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


# ============================================================
# V5 — Régénération intelligente avec feedback structuré
# ============================================================

from pydantic import BaseModel, Field

# Max 5 régénérations par tâche — constante partagée avec le frontend
MAX_REGENERATIONS_PER_TASK = 5

# Motifs standards pré-codés (choix multiple dans le modal frontend)
VALID_REGENERATION_REASONS = {
    "too_generic",           # Trop générique, manque de spécificité projet
    "wrong_norm",            # Mauvaise norme citée ou mal référencée
    "missing_info",          # Informations importantes manquantes
    "wrong_tone",            # Ton inapproprié (trop marketing, trop sec...)
    "factual_error",         # Erreur factuelle (valeur, calcul, référence)
    "wrong_structure",       # Structure / plan du document à revoir
    "too_long",              # Trop long / trop détaillé
    "too_short",             # Trop court / manque de profondeur
    "language_issue",        # Français maladroit, fautes, anglicismes
    "assumption_wrong",      # Hypothèse posée non valable pour ce projet
    "citation_missing",      # Références / sources manquantes
    "other",                 # Motif libre uniquement
}


class RegenerateRequest(BaseModel):
    reasons: list[str] = Field(default_factory=list,
                                description="Motifs cochés parmi VALID_REGENERATION_REASONS")
    custom_feedback: str = Field(default="", max_length=2000,
                                  description="Texte libre complémentaire")
    target_sections: list[str] = Field(default_factory=list,
                                        description="Sections à régénérer "
                                                    "(titres/numéros). Vide = régénération complète.")
    upgrade_model: bool = Field(default=False,
                                 description="Force le modèle supérieur "
                                             "(Haiku → Sonnet → Opus) pour cette régénération")


@router.post("/{task_id}/regenerate", status_code=202)
async def regenerate_task(
    task_id: str,
    body: RegenerateRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
):
    """Régénère une tâche complétée avec feedback structuré.

    Règles :
      - Tâche doit être 'completed' ou 'failed'
      - Maximum 5 régénérations par task (MAX_REGENERATIONS_PER_TASK)
      - Motifs validés contre VALID_REGENERATION_REASONS
      - Quota tokens vérifié (TokenQuotaExceeded → 402)
      - Le feedback est injecté dans input_params.regeneration_context
        et sera consommé par l'agent au prochain dispatch.
    """
    if user.role == "viewer":
        raise HTTPException(403, "Droits insuffisants")

    # Validation des motifs
    invalid = [r for r in body.reasons if r not in VALID_REGENERATION_REASONS]
    if invalid:
        raise HTTPException(400, f"Motifs invalides : {invalid}. "
                                  f"Valides : {sorted(VALID_REGENERATION_REASONS)}")

    if not body.reasons and not body.custom_feedback.strip():
        raise HTTPException(400, "Au moins un motif ou un feedback texte est requis")

    admin = get_supabase_admin()
    task = admin.table("tasks").select("*").eq(
        "id", task_id,
    ).eq("organization_id", user.organization_id).maybe_single().execute()
    if not task.data:
        raise HTTPException(404, "Tâche introuvable")

    if task.data["status"] not in ("completed", "failed"):
        raise HTTPException(400, f"Tâche en statut '{task.data['status']}' — "
                                  "attendez qu'elle termine avant de régénérer")

    # Limite de régénérations
    current_count = int(task.data.get("regeneration_count") or 0)
    if current_count >= MAX_REGENERATIONS_PER_TASK:
        raise HTTPException(429,
            f"Limite atteinte : {MAX_REGENERATIONS_PER_TASK} régénérations maximum par tâche. "
            f"Crée une nouvelle tâche avec des inputs révisés.")

    # Check quota tokens
    from app.services.token_quota import TokenQuotaExceeded, check_quota_available
    try:
        await check_quota_available(user.organization_id, estimated_tokens=0)
    except TokenQuotaExceeded as e:
        # 402 Payment Required : sémantiquement correct pour "faut payer ou attendre"
        raise HTTPException(402, e.user_message)

    # Enrichit input_params avec le contexte de régénération
    input_params = task.data.get("input_params") or {}
    next_attempt = current_count + 1

    input_params["regeneration_context"] = {
        "attempt": next_attempt,
        "max_attempts": MAX_REGENERATIONS_PER_TASK,
        "reasons": body.reasons,
        "custom_feedback": body.custom_feedback.strip(),
        "target_sections": body.target_sections,
        "previous_output_preview": (task.data.get("result_preview") or "")[:2000],
        "upgrade_model": body.upgrade_model,
        "requested_at": _now_iso(),
        "requested_by": user.user_id,
    }

    admin.table("tasks").update({
        "status": "queued",
        "error_message": None,
        "input_params": input_params,
        "regeneration_count": next_attempt,
    }).eq("id", task_id).execute()

    # Enqueue
    pool = await _get_redis_pool()
    await pool.enqueue_job("run_task", task_id)

    await audit_log(
        action="task_regenerated",
        organization_id=user.organization_id,
        user_id=user.user_id,
        resource_type="task",
        resource_id=task_id,
        metadata={
            "attempt": next_attempt,
            "reasons": body.reasons,
            "has_custom_feedback": bool(body.custom_feedback.strip()),
            "target_sections_count": len(body.target_sections),
        },
        ip_address=request.client.host if request.client else None,
    )

    return {
        "status": "queued",
        "task_id": task_id,
        "attempt": next_attempt,
        "remaining_regenerations": MAX_REGENERATIONS_PER_TASK - next_attempt,
    }


@router.get("/{task_id}/regenerations")
async def list_regenerations(
    task_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Retourne l'historique des régénérations d'une tâche."""
    admin = get_supabase_admin()
    task = admin.table("tasks").select(
        "regeneration_count, last_regenerated_at, regeneration_history",
    ).eq("id", task_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not task.data:
        raise HTTPException(404, "Tâche introuvable")

    return {
        "count": task.data.get("regeneration_count") or 0,
        "max_per_task": MAX_REGENERATIONS_PER_TASK,
        "last_at": task.data.get("last_regenerated_at"),
        "history": task.data.get("regeneration_history") or [],
        "remaining": MAX_REGENERATIONS_PER_TASK - int(task.data.get("regeneration_count") or 0),
    }


def _now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat()
