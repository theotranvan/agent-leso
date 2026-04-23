"""Routes V4 - agents haute valeur ajoutée (dossier enquête, observations, simulation rapide, métrés IFC).

Chaque endpoint déclenche une tâche en queue via l'orchestrateur.
Les résultats sont stockés et accessibles via /tasks/{id}.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.database import get_storage, get_supabase_admin
from app.middleware import AuthUser, audit_log, check_quota, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["v4-agents"])


# ============================================================
# Modèles Pydantic
# ============================================================

class DossierEnqueteCreate(BaseModel):
    project_id: str | None = None
    project_name: str = Field(..., min_length=1, max_length=200)
    project_data: dict[str, Any]
    existing_documents: list[dict[str, Any]] = Field(default_factory=list)
    specificities: str = ""
    author: str = ""
    send_email: bool = False
    recipient_emails: list[str] = Field(default_factory=list)


class ObservationsCreate(BaseModel):
    project_id: str | None = None
    project_name: str = Field(..., min_length=1, max_length=200)
    autorite_pdf_document_id: str = Field(..., description="ID du document PDF du courrier autorité")
    project_data: dict[str, Any] = Field(default_factory=dict)
    author: str = ""
    send_email: bool = False
    recipient_emails: list[str] = Field(default_factory=list)


class SimulationRapideCreate(BaseModel):
    project_id: str | None = None
    project_name: str = Field(..., min_length=1, max_length=200)
    programme: dict[str, Any] = Field(..., description="surfaces, affectations, canton, standard")
    author: str = ""
    send_email: bool = False
    recipient_emails: list[str] = Field(default_factory=list)


class MetresCreate(BaseModel):
    project_id: str | None = None
    project_name: str = Field(..., min_length=1, max_length=200)
    ifc_document_id: str = Field(..., description="ID document IFC déjà uploadé")
    author: str = ""
    send_email: bool = False
    recipient_emails: list[str] = Field(default_factory=list)


# ============================================================
# Création d'une tâche V4 (pattern commun)
# ============================================================

async def _create_task(
    user: AuthUser,
    task_type: str,
    project_id: str | None,
    input_params: dict[str, Any],
) -> dict[str, Any]:
    """Crée une tâche en DB + enqueue dans ARQ.

    Retourne {task_id, status: 'queued'}.
    """
    await check_quota(user)

    admin = get_supabase_admin()
    task_id = str(uuid.uuid4())

    admin.table("tasks").insert({
        "id": task_id,
        "organization_id": user.organization_id,
        "user_id": user.user_id,
        "project_id": project_id,
        "task_type": task_type,
        "status": "queued",
        "input_params": input_params,
        "attempts": 0,
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    # Enqueue via ARQ
    try:
        from arq.connections import create_pool, RedisSettings
        from app.config import settings
        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await pool.enqueue_job("run_task", task_id)
        await pool.close()
    except Exception as e:
        logger.warning("Enqueue ARQ échoué (tâche restera en queued DB) : %s", e)

    audit_log(user, f"{task_type}_created", {"task_id": task_id, "project_id": project_id})
    return {"task_id": task_id, "status": "queued"}


# ============================================================
# 1. Dossier mise en enquête (APA Genève, APC Vaud)
# ============================================================

@router.post("/dossier-enquete", status_code=202)
async def create_dossier_enquete(
    body: DossierEnqueteCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Lance la génération d'un dossier de mise en enquête.

    Retourne immédiatement le task_id — le résultat est consultable via /tasks/{id}.
    """
    if not body.project_data.get("canton"):
        raise HTTPException(400, "project_data.canton requis (GE, VD, NE, FR, VS, JU)")
    if not body.project_data.get("sre_m2"):
        raise HTTPException(400, "project_data.sre_m2 requis")

    # Auto-collecte des documents du projet si project_id fourni
    existing = body.existing_documents
    if body.project_id and not existing:
        admin = get_supabase_admin()
        docs = admin.table("documents").select("id, filename, file_type").eq(
            "project_id", body.project_id,
        ).eq("organization_id", user.organization_id).execute()
        existing = [
            {"id": d["id"], "filename": d["filename"], "file_type": d["file_type"]}
            for d in (docs.data or [])
        ]

    return await _create_task(
        user, "dossier_mise_enquete", body.project_id,
        {
            "project_name": body.project_name,
            "project_data": body.project_data,
            "existing_documents": existing,
            "specificities": body.specificities,
            "author": body.author,
            "send_email": body.send_email,
            "recipient_emails": body.recipient_emails,
        },
    )


@router.get("/dossier-enquete")
async def list_dossiers_enquete(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: str | None = None,
):
    """Liste les dossiers de mise en enquête (via la table dossiers_enquete ou via tasks)."""
    admin = get_supabase_admin()
    q = admin.table("tasks").select("*").eq(
        "organization_id", user.organization_id,
    ).eq("task_type", "dossier_mise_enquete")
    if project_id:
        q = q.eq("project_id", project_id)
    result = q.order("created_at", desc=True).limit(50).execute()
    return {"dossiers": result.data or []}


# ============================================================
# 2. Réponse aux observations d'autorité (DALE / DGT / CAMAC)
# ============================================================

@router.post("/observations", status_code=202)
async def create_observations_response(
    body: ObservationsCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Lance la génération d'une lettre de réponse à un courrier d'autorité."""
    admin = get_supabase_admin()
    doc = admin.table("documents").select("id").eq(
        "id", body.autorite_pdf_document_id,
    ).eq("organization_id", user.organization_id).maybe_single().execute()
    if not doc.data:
        raise HTTPException(404, "Document courrier autorité introuvable")

    return await _create_task(
        user, "reponse_observations_autorite", body.project_id,
        {
            "project_name": body.project_name,
            "autorite_pdf_document_id": body.autorite_pdf_document_id,
            "project_data": body.project_data,
            "author": body.author,
            "send_email": body.send_email,
            "recipient_emails": body.recipient_emails,
        },
    )


@router.get("/observations")
async def list_observations(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: str | None = None,
):
    admin = get_supabase_admin()
    q = admin.table("tasks").select("*").eq(
        "organization_id", user.organization_id,
    ).eq("task_type", "reponse_observations_autorite")
    if project_id:
        q = q.eq("project_id", project_id)
    result = q.order("created_at", desc=True).limit(50).execute()
    return {"responses": result.data or []}


# ============================================================
# 3. Simulation énergétique rapide (sans IFC)
# ============================================================

@router.post("/simulation-rapide", status_code=202)
async def create_simulation_rapide(
    body: SimulationRapideCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Estimation Qh depuis programme architectural (30 secondes)."""
    programme = body.programme
    required = ["canton", "affectation", "sre_m2"]
    missing = [k for k in required if not programme.get(k)]
    if missing:
        raise HTTPException(400, f"programme.{missing[0]} requis")

    return await _create_task(
        user, "simulation_energetique_rapide", body.project_id,
        {
            "project_name": body.project_name,
            "programme": body.programme,
            "author": body.author,
            "send_email": body.send_email,
            "recipient_emails": body.recipient_emails,
        },
    )


@router.post("/simulation-rapide/sync")
async def simulation_rapide_sync(
    body: SimulationRapideCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Variante synchrone pour résultat immédiat (pas de tâche queue)."""
    from app.agent.swiss import simulation_rapide_agent

    programme = body.programme
    required = ["canton", "affectation", "sre_m2"]
    missing = [k for k in required if not programme.get(k)]
    if missing:
        raise HTTPException(400, f"programme.{missing[0]} requis")

    task_dict: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "organization_id": user.organization_id,
        "user_id": user.user_id,
        "project_id": body.project_id,
        "input_params": {
            "project_name": body.project_name,
            "programme": body.programme,
            "author": body.author,
        },
    }
    try:
        result = await simulation_rapide_agent.execute(task_dict)
        audit_log(user, "simulation_rapide_sync", {"sre_m2": programme.get("sre_m2")})
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Simulation rapide échec")
        raise HTTPException(500, f"Erreur simulation : {e}")


# ============================================================
# 4. Métrés automatiques IFC
# ============================================================

@router.post("/metres", status_code=202)
async def create_metres(
    body: MetresCreate,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Extrait SB/SU/SRE/volume/CFC depuis un IFC et produit DPGF + tableau surfaces."""
    admin = get_supabase_admin()
    doc = admin.table("documents").select("id, file_type").eq(
        "id", body.ifc_document_id,
    ).eq("organization_id", user.organization_id).maybe_single().execute()
    if not doc.data:
        raise HTTPException(404, "Document IFC introuvable")
    if doc.data.get("file_type") not in ("ifc", "ifczip"):
        raise HTTPException(400, f"Document n'est pas un IFC : {doc.data.get('file_type')}")

    return await _create_task(
        user, "metres_automatiques_ifc", body.project_id,
        {
            "project_name": body.project_name,
            "ifc_document_id": body.ifc_document_id,
            "author": body.author,
            "send_email": body.send_email,
            "recipient_emails": body.recipient_emails,
        },
    )


@router.get("/metres")
async def list_metres(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: str | None = None,
):
    admin = get_supabase_admin()
    q = admin.table("tasks").select("*").eq(
        "organization_id", user.organization_id,
    ).eq("task_type", "metres_automatiques_ifc")
    if project_id:
        q = q.eq("project_id", project_id)
    result = q.order("created_at", desc=True).limit(50).execute()
    return {"metres": result.data or []}


# ============================================================
# 5. Upload autocontrôlé (helper pour uploads rapides depuis les forms V4)
# ============================================================

@router.post("/upload")
async def upload_document_v4(
    user: Annotated[AuthUser, Depends(get_current_user)],
    file: UploadFile = File(...),
    project_id: str | None = Form(None),
    category: str = Form("v4"),
):
    """Upload rapide d'un document depuis les forms V4."""
    from app.config import settings

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(413, f"Fichier trop volumineux : {size_mb:.1f} MB")

    ext = (file.filename or "").split(".")[-1].lower() if file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Extension non autorisée : .{ext}")

    storage = get_storage()
    filename = file.filename or f"upload_{datetime.now().timestamp()}.{ext}"
    path = f"{user.organization_id}/{category}/{uuid.uuid4().hex[:8]}_{filename}"
    storage.upload(path, content, content_type=file.content_type or "application/octet-stream")

    admin = get_supabase_admin()
    doc_id = str(uuid.uuid4())
    admin.table("documents").insert({
        "id": doc_id,
        "organization_id": user.organization_id,
        "project_id": project_id,
        "filename": filename,
        "file_type": ext,
        "storage_path": path,
        "size_bytes": len(content),
        "processed": False,
    }).execute()

    return {"document_id": doc_id, "filename": filename, "size_mb": round(size_mb, 2)}
