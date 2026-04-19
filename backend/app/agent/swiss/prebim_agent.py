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
