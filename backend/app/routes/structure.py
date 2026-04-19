"""Routes structure : création modèle, génération SAF, import résultats, note SIA."""
import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.agent.swiss.structure_agent import build_saf_and_sheet, run_structure_note_pipeline
from app.database import get_storage, get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user
from app.models.structural import StructuralModelInput

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/structure", tags=["structure"])


@router.post("/models", status_code=201)
async def create_structural_model(
    body: StructuralModelInput,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    result = admin.table("structural_models").insert({
        "organization_id": user.organization_id,
        "project_id": body.project_id,
        "name": body.name,
        "referentiel": body.project.referentiel,
        "material_default": body.material_default,
        "exposure_class": body.project.exposure_class,
        "consequence_class": body.project.consequence_class,
        "seismic_zone": body.project.seismic_zone,
        "nodes": [n.model_dump() for n in body.nodes],
        "members": [m.model_dump() for m in body.members],
        "supports": [s.model_dump() for s in body.supports],
        "load_cases": [lc.model_dump() for lc in body.load_cases],
        "combinations": [c.model_dump() for c in body.combinations],
        "status": "draft",
    }).execute()
    return result.data[0] if result.data else {}


@router.get("/models")
async def list_structural_models(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: str | None = None,
):
    admin = get_supabase_admin()
    q = admin.table("structural_models").select("*").eq("organization_id", user.organization_id)
    if project_id:
        q = q.eq("project_id", project_id)
    r = q.order("created_at", desc=True).execute()
    return {"models": r.data or []}


@router.get("/models/{model_id}")
async def get_structural_model(
    model_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    admin = get_supabase_admin()
    m = admin.table("structural_models").select("*").eq("id", model_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not m.data:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    return m.data


@router.post("/models/{model_id}/generate-saf")
async def generate_saf(
    model_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Génère le fichier SAF + la notice pour l'ingénieur."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    m = admin.table("structural_models").select("*").eq("id", model_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not m.data:
        raise HTTPException(status_code=404, detail="Modèle introuvable")

    # Reconstruire la structure attendue par le générateur
    model = m.data
    full_model = {
        "project": {
            "name": model["name"],
            "referentiel": model.get("referentiel", "sia"),
            "exposure_class": model.get("exposure_class", "XC2"),
            "consequence_class": model.get("consequence_class", "CC2"),
            "seismic_zone": model.get("seismic_zone", "Z1b"),
        },
        "nodes": model.get("nodes", []),
        "members": model.get("members", []),
        "supports": model.get("supports", []),
        "load_cases": model.get("load_cases", []),
        "combinations": model.get("combinations", []),
        "loads": model.get("loads", []),
    }

    result = build_saf_and_sheet(full_model)

    storage = get_storage()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    saf_path = f"{user.organization_id}/structure/{model_id}/saf_{ts}.xlsx"
    notice_path = f"{user.organization_id}/structure/{model_id}/notice_ingenieur_{ts}.md"

    storage.upload(saf_path, result["saf_xlsx"],
                   content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    storage.upload(notice_path, result["notice_md"].encode("utf-8"),
                   content_type="text/markdown")

    admin.table("structural_models").update({
        "status": "saf_generated",
        "saf_file_url": saf_path,
    }).eq("id", model_id).execute()

    await audit_log(
        action="structural_saf_generated",
        organization_id=user.organization_id,
        user_id=user.id,
        resource_type="structural_model",
        resource_id=model_id,
    )

    return {
        "saf_url": storage.get_signed_url(saf_path, expires_in=604800),
        "notice_url": storage.get_signed_url(notice_path, expires_in=604800),
        "next_step": "Ouvrir le SAF dans votre logiciel (Scia, RFEM…), calculer, ré-exporter en SAF, puis POST /structure/models/{id}/import-results",
    }


@router.post("/models/{model_id}/import-results")
async def import_saf_results(
    model_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    saf_results: UploadFile = File(..., description="SAF .xlsx enrichi avec résultats du logiciel"),
    author_name: str | None = Form(None),
    engineer_validated: bool = Form(False, description="L'ingénieur confirme avoir vérifié le modèle et les résultats"),
):
    """Import du SAF enrichi, double-check, génération de la note SIA."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    if not engineer_validated:
        raise HTTPException(
            status_code=400,
            detail="La note ne peut être générée qu'après validation explicite par un ingénieur (engineer_validated=true)",
        )

    admin = get_supabase_admin()
    m = admin.table("structural_models").select("*").eq("id", model_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not m.data:
        raise HTTPException(status_code=404, detail="Modèle introuvable")

    saf_bytes = await saf_results.read()

    # Reconstruct full model
    model = m.data
    full_model = {
        "project": {
            "name": model["name"],
            "referentiel": model.get("referentiel", "sia"),
            "exposure_class": model.get("exposure_class"),
            "consequence_class": model.get("consequence_class"),
            "seismic_zone": model.get("seismic_zone"),
        },
        "nodes": model.get("nodes", []),
        "members": model.get("members", []),
        "supports": model.get("supports", []),
        "load_cases": model.get("load_cases", []),
        "combinations": model.get("combinations", []),
        "loads": model.get("loads", []),
    }

    project_name = ""
    project_address = ""
    if model.get("project_id"):
        p = admin.table("projects").select("name, address").eq("id", model["project_id"]).maybe_single().execute()
        if p.data:
            project_name = p.data.get("name", "")
            project_address = p.data.get("address", "")

    result = await run_structure_note_pipeline(
        structural_model=full_model,
        saf_results_bytes=saf_bytes,
        project_name=project_name,
        project_address=project_address,
        author=author_name or "",
    )

    storage = get_storage()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Store résultats SAF
    results_path = f"{user.organization_id}/structure/{model_id}/saf_results_{ts}.xlsx"
    storage.upload(results_path, saf_bytes,
                   content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Store PDF note
    pdf_path = f"{user.organization_id}/structure/{model_id}/note_sia_{ts}.pdf"
    storage.upload(pdf_path, result["pdf_bytes"], content_type="application/pdf")

    admin.table("structural_models").update({
        "status": "note_generated",
        "results_file_url": results_path,
        "results_parsed": result["results_parsed"],
        "double_check_result": result["double_check"],
        "engineer_validated_by": user.id,
        "engineer_validated_at": datetime.utcnow().isoformat(),
    }).eq("id", model_id).execute()

    admin.table("documents").insert({
        "organization_id": user.organization_id,
        "project_id": model.get("project_id"),
        "filename": f"note_calcul_SIA_{ts}.pdf",
        "file_type": "pdf",
        "storage_path": pdf_path,
        "processed": True,
    }).execute()

    return {
        "pdf_url": storage.get_signed_url(pdf_path, expires_in=604800),
        "max_utilization": result["max_utilization"],
        "compliant": result["compliant"],
        "double_check": result["double_check"],
        "preview": result["note_md"][:500],
    }
