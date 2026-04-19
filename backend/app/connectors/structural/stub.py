"""Stub structural connector - portique béton réaliste pour dev/tests."""
from __future__ import annotations

import logging
import time

from app.connectors.structural.base import (
    AnalysisResult,
    AnomalyLevel,
    MemberCheck,
    StructuralAnomaly,
    StructuralConnector,
    StructuralInputs,
)

logger = logging.getLogger(__name__)


class StubStructuralConnector(StructuralConnector):
    """Retourne un AnalysisResult représentatif d'un portique BA simple.

    Scénario : 2 poutres + 2 poteaux, classe de conséquence CC2, tout conforme.
    Ne fait AUCUN calcul réel.
    """

    name = "stub"

    def validate_inputs(self, inputs: StructuralInputs) -> list[str]:
        return []

    def analyze(self, inputs: StructuralInputs) -> AnalysisResult:
        start = time.monotonic()

        checks = [
            MemberCheck(
                member_id="B1_poutre_rdc",
                check_name="ULS_bending_SIA_262",
                utilization_ratio=0.72,
                compliant=True,
                details={"M_kNm_sw": 45.2, "V_kN_sw": 28.1, "N_kN_sw": 0.0},
            ),
            MemberCheck(
                member_id="B2_poutre_etage",
                check_name="ULS_bending_SIA_262",
                utilization_ratio=0.68,
                compliant=True,
                details={"M_kNm_sw": 41.5, "V_kN_sw": 26.3, "N_kN_sw": 0.0},
            ),
            MemberCheck(
                member_id="P1_poteau_rdc",
                check_name="ULS_compression_SIA_262",
                utilization_ratio=0.58,
                compliant=True,
                details={"M_kNm_sw": 5.1, "N_kN_sw": 285.0},
            ),
            MemberCheck(
                member_id="P2_poteau_rdc",
                check_name="ULS_compression_SIA_262",
                utilization_ratio=0.61,
                compliant=True,
                details={"M_kNm_sw": 4.9, "N_kN_sw": 298.0},
            ),
            MemberCheck(
                member_id="B1_poutre_rdc",
                check_name="SLS_deflection_SIA_262",
                utilization_ratio=0.85,
                compliant=True,
                details={"deflection_mm": 17.0, "limit_mm": 20.0},
            ),
        ]

        anomalies = [
            StructuralAnomaly(
                member_id="B1_poutre_rdc",
                check_type="beam_M_qL2_8",
                level=AnomalyLevel.INFO,
                message="Double-check analytique OK : écart 3.2% < 10%",
                analytical_value=46.7,
                software_value=45.2,
                divergence_pct=3.2,
            ),
            StructuralAnomaly(
                member_id="P1_poteau_rdc",
                check_type="column_N_sum",
                level=AnomalyLevel.INFO,
                message="Double-check analytique OK : écart 1.4%",
                analytical_value=281.0,
                software_value=285.0,
                divergence_pct=1.4,
            ),
        ]

        max_util = max(c.utilization_ratio for c in checks)
        elapsed = time.monotonic() - start

        logger.info("StubStructuralConnector retourne portique BA (%.2fs)", elapsed)

        return AnalysisResult(
            compliant=True,
            max_utilization=max_util,
            member_checks=checks,
            anomalies=anomalies,
            engine_used=self.name,
            computation_seconds=elapsed,
            warnings=[
                "STUB — valeurs factices non équivalentes à un calcul réel SIA 260-267",
            ],
            raw_output={
                "scenario": "portique_BA_2poutres_2poteaux",
                "referentiel": inputs.referentiel,
                "exposure": inputs.exposure_class,
            },
        )
