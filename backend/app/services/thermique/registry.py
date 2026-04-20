"""Registry compatibility V2 — délègue aux connectors V3.

Ce fichier remplace l'ancien registry V2 et garde la signature publique.
Les routes existantes (`from app.services.thermique.registry import get_engine`)
continuent de fonctionner, mais elles utilisent désormais les connectors V3.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.connectors.thermic import SimulationResult as V3SimulationResult, ThermicInputs
from app.connectors.thermic.gbxml_generator import GbxmlGenerator
from app.connectors.thermic.lesosai_file import LesosaiFileConnector as V3LesosaiFileConnector
from app.connectors.thermic.stub import StubThermicConnector
from app.services.thermique.engine_interface import ThermalEngine, ThermalEngineResult

logger = logging.getLogger(__name__)


def _v3_to_v2_result(r: V3SimulationResult) -> ThermalEngineResult:
    """Convertit SimulationResult (V3, kWh) → ThermalEngineResult (V2, MJ)."""

    def kwh_to_mj(kwh: float | None) -> float | None:
        return round(kwh * 3.6, 1) if kwh is not None else None

    qww_kwh = (r.ep_kwh_m2_an - r.qh_kwh_m2_an) if r.ep_kwh_m2_an else 0.0

    return ThermalEngineResult(
        qh_mj_m2_an=kwh_to_mj(r.qh_kwh_m2_an) or 0.0,
        qww_mj_m2_an=kwh_to_mj(qww_kwh) or 0.0,
        e_mj_m2_an=kwh_to_mj(r.ep_kwh_m2_an) or 0.0,
        qh_limite_mj_m2_an=kwh_to_mj(r.qh_limite_kwh_m2_an),
        compliant=r.compliant,
        warnings=r.warnings,
        engine_used=r.engine_used,
        raw_results={
            **r.raw_output,
            "energy_class": r.energy_class.value if r.energy_class else None,
            "idc_kwh_m2_an": r.idc_kwh_m2_an,
        },
    )


class _ConnectorAdapter(ThermalEngine):
    """Adapte un ThermicConnector V3 vers l'interface ThermalEngine V2."""

    def __init__(self, connector: Any, name: str) -> None:
        self._connector = connector
        self.name = name

    async def prepare_model(self, thermal_model: dict) -> dict:
        ifc_path = thermal_model.get("ifc_path")
        warnings: list[str] = []
        if ifc_path and Path(str(ifc_path)).exists():
            inputs = ThermicInputs(
                ifc_path=Path(ifc_path),
                canton=thermal_model.get("canton", "GE"),
                affectation=thermal_model.get("affectation", "logement_collectif"),
                operation_type=thermal_model.get("operation_type", "neuf"),
                standard=thermal_model.get("standard", "sia_380_1"),
                sre_m2=thermal_model.get("sre_m2"),
            )
            try:
                warnings = self._connector.validate_inputs(inputs)
            except Exception as exc:
                warnings = [f"Validation échouée : {exc}"]
        else:
            warnings = ["Pas de fichier IFC fourni : le modèle est construit depuis JSON"]

        zones = thermal_model.get("zones") or []
        total_area = sum(float(z.get("area", 0) or 0) for z in zones)
        return {
            "model": thermal_model,
            "warnings": warnings,
            "sre_total_m2": total_area or thermal_model.get("sre_m2") or 0,
            "prepared_at": "now",
        }

    async def submit(self, payload: dict) -> str:
        return f"{self.name}_submitted"

    async def fetch_results(self, job_id: str) -> ThermalEngineResult | None:
        return None

    def is_synchronous(self) -> bool:
        return self.name in ("lesosai_stub", "gbxml")

    async def compute(self, thermal_model: dict) -> ThermalEngineResult:
        """Compat V2 : le stub expose compute() directement."""
        ifc_path = thermal_model.get("ifc_path")
        systems = thermal_model.get("systems") or {}
        heating = systems.get("heating") if isinstance(systems, dict) else None
        vector = "gaz"
        if isinstance(heating, dict) and heating.get("vector"):
            vector = heating["vector"]

        inputs = ThermicInputs(
            ifc_path=Path(ifc_path) if ifc_path else Path("/dev/null"),
            canton=thermal_model.get("canton", "GE"),
            affectation=thermal_model.get("affectation", "logement_collectif"),
            operation_type=thermal_model.get("operation_type", "neuf"),
            standard=thermal_model.get("standard", "sia_380_1"),
            sre_m2=thermal_model.get("sre_m2"),
            heating_vector=vector,
        )
        result = self._connector.simulate(inputs)
        return _v3_to_v2_result(result)


_ENGINES: dict[str, ThermalEngine] = {
    "lesosai_stub": _ConnectorAdapter(StubThermicConnector(), "lesosai_stub"),
    "lesosai_file": _ConnectorAdapter(V3LesosaiFileConnector(), "lesosai_file"),
    "gbxml": _ConnectorAdapter(GbxmlGenerator(), "gbxml"),
}


def get_engine(name: str) -> ThermalEngine:
    """Retourne un moteur thermique par nom."""
    engine = _ENGINES.get(name)
    if not engine:
        raise ValueError(f"Moteur inconnu : {name}. Disponibles : {list(_ENGINES.keys())}")
    return engine


def list_engines() -> list[dict]:
    return [
        {
            "name": "lesosai_stub",
            "label": "Calcul indicatif rapide (stub)",
            "description": "Estimation approximative - avant-projet uniquement.",
            "use_for": ["avant_projet", "test"],
        },
        {
            "name": "lesosai_file",
            "label": "Export vers Lesosai (watched-folder)",
            "description": "Génère gbXML, attend le CECB XML en retour (jusqu'à 30 min).",
            "use_for": ["production", "justificatif_officiel"],
        },
        {
            "name": "gbxml",
            "label": "Générateur gbXML V3",
            "description": "IFC → gbXML v0.37 + calcul Qh simplifié HDD cantonaux.",
            "use_for": ["export_externe", "avant_projet"],
        },
    ]
