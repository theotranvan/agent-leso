"""Routes pré-BIM : extraction spec, génération IFC, validation."""
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.agent.swiss.prebim_agent import run_prebim_from_spec, run_prebim_from_text
from app.database import get_storage, get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user
from app.models.bim import PreBIMFromSpecRequest, PreBIMFromTextRequest
from app.services.bim.wall_library import list_compositions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bim", tags=["bim"])


@router.get("/compositions")
async def get_compositions():
    """Liste les compositions de parois disponibles."""
    return {"compositions": list_compositions()}


@router.post("/premodel/from-text", status_code=201)
async def premodel_from_text(
    body: PreBIMFromTextRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Génère un pré-modèle IFC depuis un programme textuel."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    try:
        result = await run_prebim_from_text(body.program_text, body.hints)
    except Exception as e:
        logger.exception("Génération pré-BIM échouée")
        raise HTTPException(status_code=500, detail=f"Génération échouée : {e}")

    return _persist_premodel(user, body.project_id, result)


@router.post("/premodel/from-spec", status_code=201)
async def premodel_from_spec(
    body: PreBIMFromSpecRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Génère un pré-modèle IFC depuis une spec déjà formée (cas édition)."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    try:
        result = await run_prebim_from_spec(body.spec.model_dump())
    except Exception as e:
        logger.exception("Génération pré-BIM échouée")
        raise HTTPException(status_code=500, detail=f"Génération échouée : {e}")

    return _persist_premodel(user, body.project_id, result)


def _persist_premodel(user: AuthUser, project_id: str | None, result: dict) -> dict:
    """Persiste l'IFC généré + bim_premodels record."""
    admin = get_supabase_admin()
    storage = get_storage()

    ifc_path = Path(result["ifc_path"])
    if not ifc_path.exists():
        raise HTTPException(status_code=500, detail="Fichier IFC non généré")

    ifc_bytes = ifc_path.read_bytes()
    ifc_path.unlink(missing_ok=True)

    premodel_id = str(uuid.uuid4())
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    storage_path = f"{user.organization_id}/bim/{premodel_id}/premodel_{ts}.ifc"
    storage.upload(storage_path, ifc_bytes, content_type="application/x-step")

    spec = result.get("spec", {})
    admin.table("bim_premodels").insert({
        "id": premodel_id,
        "organization_id": user.organization_id,
        "project_id": project_id,
        "name": spec.get("project_name", "Pré-modèle"),
        "source_inputs": {"spec": spec},
        "generated_ifc_url": storage_path,
        "generation_report": result.get("report", {}),
        "status": "awaiting_review",
    }).execute()

    # Document record
    admin.table("documents").insert({
        "organization_id": user.organization_id,
        "project_id": project_id,
        "filename": f"premodel_{ts}.ifc",
        "file_type": "ifc",
        "storage_path": storage_path,
        "processed": True,
    }).execute()

    return {
        "premodel_id": premodel_id,
        "ifc_url": storage.get_signed_url(storage_path, expires_in=604800),
        "spec": spec,
        "confidence": result.get("confidence"),
        "warnings": result.get("warnings"),
        "report": result.get("report"),
    }


@router.get("/premodels")
async def list_premodels(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: str | None = None,
):
    admin = get_supabase_admin()
    q = admin.table("bim_premodels").select("*").eq("organization_id", user.organization_id)
    if project_id:
        q = q.eq("project_id", project_id)
    r = q.order("created_at", desc=True).execute()
    return {"premodels": r.data or []}


@router.post("/premodels/{premodel_id}/validate")
async def validate_premodel(
    premodel_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Marque le pré-modèle comme validé par l'utilisateur après inspection dans le viewer."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    r = admin.table("bim_premodels").update({
        "validated": True,
        "validated_by": user.id,
        "validated_at": datetime.utcnow().isoformat(),
        "status": "validated",
    }).eq("id", premodel_id).eq("organization_id", user.organization_id).execute()

    if not r.data:
        raise HTTPException(status_code=404, detail="Pré-modèle introuvable")

    await audit_log(
        action="bim_premodel_validated",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="bim_premodel",
        resource_id=premodel_id,
    )
    return r.data[0]


@router.post("/extract-envelope")
async def extract_envelope(
    user: Annotated[AuthUser, Depends(get_current_user)],
    body: dict,
):
    """Extrait l'enveloppe thermique d'un IFC pour pré-remplir le justificatif SIA 380/1.

    Body : { "ifc_document_id": "..." }  ou  { "ifc_storage_path": "..." }
    Retourne surfaces, U-values, volume, complétude et champs à compléter.
    """
    from app.services.ifc_thermal_extractor import extract_envelope_for_thermal

    admin = get_supabase_admin()
    storage = get_storage()

    doc_id = body.get("ifc_document_id")
    storage_path = body.get("ifc_storage_path")

    if doc_id:
        doc = (
            admin.table("documents").select("storage_path")
            .eq("id", doc_id).eq("organization_id", user.organization_id)
            .maybe_single().execute()
        )
        if not doc.data:
            raise HTTPException(status_code=404, detail="Document IFC introuvable")
        storage_path = doc.data["storage_path"]

    if not storage_path:
        raise HTTPException(status_code=400, detail="ifc_document_id ou ifc_storage_path requis")

    try:
        ifc_bytes = storage.download(storage_path)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Téléchargement IFC échoué : {e}")

    result = extract_envelope_for_thermal(ifc_bytes)
    if not result.get("extracted"):
        raise HTTPException(
            status_code=422,
            detail=result.get("error", "Impossible de lire la maquette IFC"),
        )
    return result
