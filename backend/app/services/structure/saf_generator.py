"""Shim V2 → délègue à app.connectors.structural.saf_generator.

Maintient la signature `generate_saf_xlsx(structural_model: dict) -> bytes`
utilisée par app/agent/swiss/structure_agent.py.
"""
from __future__ import annotations

import logging
from typing import Any

from app.connectors.structural import StructuralInputs
from app.connectors.structural.saf_generator import SafGenerator

logger = logging.getLogger(__name__)


def generate_saf_xlsx(structural_model: dict) -> bytes:
    """Génère un fichier SAF xlsx depuis un modèle structurel JSON V2.

    Accepte les clés :
      - nodes, members, supports, loads (optionnel)
      - project_info : dict avec referentiel, exposure_class, consequence_class
    """
    info = structural_model.get("project_info") or {}
    inputs = StructuralInputs(
        ifc_path=None,
        model_data={
            "nodes": structural_model.get("nodes", []),
            "members": structural_model.get("members", []),
            "supports": structural_model.get("supports", []),
            "loads": structural_model.get("loads", []),
        },
        referentiel=info.get("referentiel", "sia"),
        exposure_class=info.get("exposure_class", "XC2"),
        consequence_class=info.get("consequence_class", "CC2"),
        seismic_zone=info.get("seismic_zone", "Z1b"),
        material_default=info.get("material_default", "C30/37"),
    )
    gen = SafGenerator()
    return gen.generate_saf_bytes(inputs)
