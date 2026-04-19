"""Routes thermique : modèles, pipeline Lesosai stub/file, import résultats."""
import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.agent.swiss.thermique_agent import run_thermal_pipeline
from app.database import get_storage, get_supabase_admin
from app.middleware import AuthUser, audit_log, get_current_user
from app.models.thermal import ThermalModelInput, ThermalRunRequest
from app.services.thermique.lesosai_file import (
    build_operator_sheet_markdown,
    parse_lesosai_results_pdf,
    serialize_to_lesosai_xml,
)
from app.services.thermique.registry import get_engine, list_engines

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/thermique", tags=["thermique"])


@router.get("/engines")
async def engines():
    """Liste les moteurs thermiques disponibles."""
    return {"engines": list_engines()}


@router.post("/models", status_code=201)
async def create_thermal_model(
    body: ThermalModelInput,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Crée un modèle thermique."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    payload = body.model_dump()
    payload["organization_id"] = user.organization_id
    # Sérialise les listes imbriquées en JSON compatible Supabase
    result = admin.table("thermal_models").insert({
        "organization_id": user.organization_id,
        "project_id": payload.get("project_id"),
        "name": payload["name"],
        "canton": payload["canton"],
        "affectation": payload.get("affectation"),
        "operation_type": payload.get("operation_type"),
        "standard": payload.get("standard", "sia_380_1"),
        "zones": payload.get("zones", []),
        "walls": payload.get("walls", []),
        "openings": payload.get("openings", []),
        "thermal_bridges": payload.get("thermal_bridges", []),
        "systems": payload.get("systems", {}),
        "hypotheses": payload.get("hypotheses", {}),
        "status": "draft",
    }).execute()
    return result.data[0] if result.data else {}


@router.get("/models")
async def list_thermal_models(
    user: Annotated[AuthUser, Depends(get_current_user)],
    project_id: str | None = None,
):
    admin = get_supabase_admin()
    q = admin.table("thermal_models").select("*").eq("organization_id", user.organization_id)
    if project_id:
        q = q.eq("project_id", project_id)
    result = q.order("created_at", desc=True).execute()
    return {"models": result.data or []}


@router.get("/models/{model_id}")
async def get_thermal_model(
    model_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    admin = get_supabase_admin()
    m = admin.table("thermal_models").select("*").eq("id", model_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not m.data:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    return m.data


@router.post("/models/{model_id}/run")
async def run_thermal(
    model_id: str,
    body: ThermalRunRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Lance le pipeline thermique : stub (synchrone) ou file (génère XML + fiche)."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    m = admin.table("thermal_models").select("*").eq("id", model_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not m.data:
        raise HTTPException(status_code=404, detail="Modèle introuvable")

    model = m.data
    engine_name = body.engine

    # Charge les infos projet pour contexte
    project_name = ""
    project_address = ""
    if model.get("project_id"):
        p = admin.table("projects").select("name, address").eq("id", model["project_id"]).maybe_single().execute()
        if p.data:
            project_name = p.data.get("name", "")
            project_address = p.data.get("address", "")

    storage = get_storage()

    # Pour engine 'lesosai_file' : générer XML + fiche saisie
    if engine_name == "lesosai_file":
        xml_bytes = serialize_to_lesosai_xml(model)
        engine = get_engine("lesosai_file")
        prep = await engine.prepare_model(model)
        sheet_md = build_operator_sheet_markdown(model, prep)

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        xml_path = f"{user.organization_id}/thermique/{model_id}/lesosai_{ts}.xml"
        sheet_path = f"{user.organization_id}/thermique/{model_id}/fiche_saisie_{ts}.md"
        storage.upload(xml_path, xml_bytes, content_type="application/xml")
        storage.upload(sheet_path, sheet_md.encode("utf-8"), content_type="text/markdown")

        # Log exchange
        admin.table("lesosai_exchanges").insert({
            "organization_id": user.organization_id,
            "thermal_model_id": model_id,
            "direction": "out",
            "mode": "file_xml",
            "payload_url": xml_path,
            "status": "generated",
        }).execute()

        admin.table("thermal_models").update({
            "status": "sent_to_engine",
            "engine_connector": engine_name,
        }).eq("id", model_id).execute()

        await audit_log(
            action="thermal_lesosai_file_generated",
            organization_id=user.organization_id,
            user_id=user.id,
            resource_type="thermal_model",
            resource_id=model_id,
        )

        return {
            "engine": engine_name,
            "lesosai_xml_url": storage.get_signed_url(xml_path, expires_in=604800),
            "operator_sheet_url": storage.get_signed_url(sheet_path, expires_in=604800),
            "warnings": prep.get("warnings", []),
            "next_step": "Saisir dans Lesosai (aidé par la fiche), exporter résultats PDF, puis utiliser POST /thermique/models/{id}/import-results",
        }

    # Engine stub : calcul immédiat + justificatif
    result = await run_thermal_pipeline(
        thermal_model=model,
        engine_name=engine_name,
        project_name=project_name,
        project_address=project_address,
        author=body.author_name or "",
    )

    # Upload PDF
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pdf_path = f"{user.organization_id}/thermique/{model_id}/justificatif_{ts}.pdf"
    storage.upload(pdf_path, result["pdf_bytes"], content_type="application/pdf")
    pdf_url = storage.get_signed_url(pdf_path, expires_in=604800)

    admin.table("thermal_models").update({
        "status": "completed",
        "engine_connector": engine_name,
        "results": result.get("results") or {},
    }).eq("id", model_id).execute()

    # Enregistre document
    admin.table("documents").insert({
        "organization_id": user.organization_id,
        "project_id": model.get("project_id"),
        "filename": f"justificatif_SIA_380_1_{ts}.pdf",
        "file_type": "pdf",
        "storage_path": pdf_path,
        "processed": True,
    }).execute()

    return {
        "engine": engine_name,
        "pdf_url": pdf_url,
        "results": result.get("results"),
        "warnings": result.get("warnings"),
        "preview": result["justificatif_md"][:500],
    }


@router.post("/models/{model_id}/import-results")
async def import_lesosai_results(
    model_id: str,
    user: Annotated[AuthUser, Depends(get_current_user)],
    pdf: UploadFile = File(..., description="Rapport PDF exporté depuis Lesosai"),
    author_name: str | None = Form(None),
):
    """Import du PDF résultats Lesosai après saisie utilisateur.

    Extrait Qh/Qww/E, met à jour le modèle, génère le justificatif final.
    """
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Droits insuffisants")

    admin = get_supabase_admin()
    m = admin.table("thermal_models").select("*").eq("id", model_id).eq("organization_id", user.organization_id).maybe_single().execute()
    if not m.data:
        raise HTTPException(status_code=404, detail="Modèle introuvable")

    pdf_bytes = await pdf.read()
    parsed = parse_lesosai_results_pdf(pdf_bytes)

    if not parsed:
        raise HTTPException(status_code=400, detail="Impossible d'extraire les résultats du PDF Lesosai")

    # Stocke le PDF source
    storage = get_storage()
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    source_path = f"{user.organization_id}/thermique/{model_id}/lesosai_results_{ts}.pdf"
    storage.upload(source_path, pdf_bytes, content_type="application/pdf")

    admin.table("lesosai_exchanges").insert({
        "organization_id": user.organization_id,
        "thermal_model_id": model_id,
        "direction": "in",
        "mode": "file_xml",
        "payload_url": source_path,
        "status": "parsed",
    }).execute()

    # MAJ modèle et statut
    model = m.data
    model["results"] = parsed
    admin.table("thermal_models").update({
        "status": "results_received",
        "results": parsed,
    }).eq("id", model_id).execute()

    # Génère le justificatif final en passant les résultats extraits
    # On remplace les résultats du stub par les vrais
    from app.agent.swiss.thermique_agent import run_thermal_pipeline as _run
    project_name = ""
    project_address = ""
    if model.get("project_id"):
        p = admin.table("projects").select("name, address").eq("id", model["project_id"]).maybe_single().execute()
        if p.data:
            project_name = p.data.get("name", "")
            project_address = p.data.get("address", "")

    # Injecte les résultats manuellement via la clé 'results' dans le model avant pipeline
    # La fonction utilise 'lesosai_stub' pour calculer, ici on veut bypass ça
    # On appelle donc directement le LLM avec les résultats parsés
    from app.agent.router import call_llm
    from app.agent.swiss.prompts_ch import get_prompt_ch
    from app.services.pdf_generator import markdown_to_html, render_pdf_from_html, render_visa_block

    system = get_prompt_ch("thermique_ch")
    user_content = f"""Rédiger le justificatif thermique SIA 380/1 FINAL à partir des résultats officiels Lesosai.

PROJET : {project_name}
Canton : {model.get('canton')}
Affectation : {model.get('affectation')}
Opération : {model.get('operation_type')}

RÉSULTATS OFFICIELS LESOSAI (extraits du PDF) :
- Qh = {parsed.get('qh_mj_m2_an')} MJ/m²/an
- Qww = {parsed.get('qww_mj_m2_an')} MJ/m²/an
- E = {parsed.get('e_mj_m2_an')} MJ/m²/an
- Qh limite = {parsed.get('qh_limite_mj_m2_an')} MJ/m²/an
- Conforme (Lesosai) : {parsed.get('compliant')}

Produire le justificatif complet en markdown avec toutes les sections habituelles et les résultats Lesosai officiels."""

    llm_result = await call_llm(
        task_type="justificatif_sia_380_1",
        system_prompt=system,
        user_content=user_content,
        max_tokens=6000,
        temperature=0.1,
    )
    md = llm_result["text"]
    body_html = markdown_to_html(md) + render_visa_block(author=author_name or "", role="Thermicien")
    pdf_final = render_pdf_from_html(
        body_html=body_html,
        title="Justificatif SIA 380/1 (résultats Lesosai)",
        project_name=project_name,
        project_address=project_address,
        author=author_name or "",
        reference=f"SIA380-1-FINAL-{ts}",
    )

    final_path = f"{user.organization_id}/thermique/{model_id}/justificatif_final_{ts}.pdf"
    storage.upload(final_path, pdf_final, content_type="application/pdf")

    admin.table("thermal_models").update({"status": "completed"}).eq("id", model_id).execute()
    admin.table("documents").insert({
        "organization_id": user.organization_id,
        "project_id": model.get("project_id"),
        "filename": f"justificatif_SIA_380_1_FINAL_{ts}.pdf",
        "file_type": "pdf",
        "storage_path": final_path,
        "processed": True,
    }).execute()

    return {
        "pdf_url": storage.get_signed_url(final_path, expires_in=604800),
        "results": parsed,
        "preview": md[:500],
    }
