"""Stub thermic connector - retourne des valeurs réalistes pour dev/tests.

Ne fait AUCUN calcul réel. Toujours identifier ce connecteur via engine_used='stub'
et ne jamais l'utiliser pour produire un justificatif officiel.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from app.connectors.thermic.base import (
    ConnectorError,
    EnergyClass,
    SimulationResult,
    ThermicConnector,
    ThermicInputs,
    limite_qh_for_affectation,
)

logger = logging.getLogger(__name__)

# Valeurs réalistes par défaut pour un logement collectif standard
DEFAULT_QH_KWH_M2_AN = 95.0     # classe D - logement existant moyen
DEFAULT_EP_KWH_M2_AN = 130.0
DEFAULT_SRE_M2 = 1000.0


class StubThermicConnector(ThermicConnector):
    """Retourne un SimulationResult réaliste sans calcul réel."""

    name = "stub"

    def validate_inputs(self, inputs: ThermicInputs) -> list[str]:
        warnings: list[str] = []
        if inputs.ifc_path and not inputs.ifc_path.exists():
            warnings.append(f"Input path inexistant (stub ignore) : {inputs.ifc_path}")
        return warnings

    def simulate(self, inputs: ThermicInputs) -> SimulationResult:
        start = time.monotonic()
        warnings = self.validate_inputs(inputs)
        warnings.append(
            "CALCUL STUB - valeurs factices non équivalentes SIA 380/1. "
            "Ne pas utiliser pour un justificatif officiel."
        )

        sre = inputs.sre_m2 or DEFAULT_SRE_M2
        qh = DEFAULT_QH_KWH_M2_AN
        ep = DEFAULT_EP_KWH_M2_AN

        qh_limite = limite_qh_for_affectation(inputs.affectation)
        compliant = qh <= qh_limite if qh_limite else None

        elapsed = time.monotonic() - start
        logger.info("StubThermicConnector invoqué (inputs=%s, sre=%.1f)", inputs.canton, sre)

        return SimulationResult(
            qh_kwh_m2_an=qh,
            ep_kwh_m2_an=ep,
            sre_m2=sre,
            idc_kwh_m2_an=qh + 20.0,  # ECS forfait logement
            qh_limite_kwh_m2_an=qh_limite,
            energy_class=EnergyClass.D,
            compliant=compliant,
            engine_used=self.name,
            computation_seconds=elapsed,
            warnings=warnings,
            raw_output={
                "stub_note": "Valeurs statiques - ne correspondent pas à un calcul réel",
                "canton_echo": inputs.canton,
                "affectation_echo": inputs.affectation,
            },
        )
