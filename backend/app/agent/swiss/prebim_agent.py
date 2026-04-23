"""Agent pré-BIM - extraction spec + génération IFC + rapport."""
import logging
from datetime import datetime
from typing import Any

from app.services.bim.premodel_generator import generate_premodel
from app.services.bim.spec_extractor import extract_spec_from_text

logger = logging.getLogger(__name__)


async def run_prebim_from_text(
    program_text: str,
    hints: dict | None = None,
) -> dict:
    """Extrait la spec + génère l'IFC."""
    spec = await extract_spec_from_text(program_text, hints)
    gen_result = generate_premodel(spec)

    return {
        "spec": spec,
        "ifc_path": gen_result["ifc_path"],
        "confidence": gen_result["confidence"],
        "warnings": gen_result["warnings"],
        "report": gen_result["report"],
    }


async def run_prebim_from_spec(spec: dict) -> dict:
    """Génère l'IFC depuis une spec déjà formée (cas édition utilisateur)."""
    from app.services.bim.spec_extractor import _validate_and_fill_defaults
    validated = _validate_and_fill_defaults(spec, {})
    gen_result = generate_premodel(validated)
    return {
        "spec": validated,
        "ifc_path": gen_result["ifc_path"],
        "confidence": gen_result["confidence"],
        "warnings": gen_result["warnings"],
        "report": gen_result["report"],
    }


async def execute(task: "dict[str, Any]") -> "dict[str, Any]":
    """Wrapper orchestrateur pour prebim_generation / prebim_extraction.

    Input params :
      - mode: 'from_text' (défaut) | 'from_spec'
      - program_text: str (si from_text)
      - spec: dict (si from_spec)
    """
    from datetime import datetime
    from typing import Any
    from app.database import get_storage, get_supabase_admin

    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    mode = params.get("mode", "from_text")

    if mode == "from_text":
        text = params.get("program_text")
        if not text:
            raise ValueError("program_text manquant")
        pipeline = await run_prebim_from_text(text)
    elif mode == "from_spec":
        spec = params.get("spec")
        if not spec:
            raise ValueError("spec manquant")
        pipeline = await run_prebim_from_spec(spec)
    else:
        raise ValueError(f"mode inconnu: {mode}")

    ifc_bytes = pipeline.get("ifc_bytes") or b""
    report = pipeline.get("report") or {}

    storage = get_storage()
    filename = f"premodel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ifc"
    path = f"{org_id}/bim/{task['id']}/{filename}"
    storage.upload(path, ifc_bytes, content_type="application/x-step")
    signed_url = storage.get_signed_url(path, expires_in=604800)

    admin = get_supabase_admin()
    admin.table("documents").insert({
        "organization_id": org_id,
        "project_id": project_id,
        "filename": filename,
        "file_type": "ifc",
        "storage_path": path,
        "processed": True,
    }).execute()

    llm = pipeline.get("llm") or {}
    preview = (
        f"Pré-modèle généré : {report.get('nb_storeys', 0)} étages, "
        f"{report.get('total_area_m2', 0)} m² — "
        f"confiance {int((report.get('confidence') or 0) * 100)}%"
    )

    return {
        "result_url": signed_url,
        "preview": preview,
        "model": llm.get("model"),
        "tokens_used": llm.get("tokens", 0),
        "cost_eur": llm.get("cost_eur", 0),
        "email_bytes": ifc_bytes,
        "email_filename": filename,
    }
