"""Shim V2 → délègue à app.connectors.structural.results_parser.

Maintient la signature `double_check(model, software_results) -> list[dict]`.
"""
from __future__ import annotations

import logging
from typing import Any

from app.connectors.structural.base import AnomalyLevel
from app.connectors.structural.results_parser import SafResultsParser

logger = logging.getLogger(__name__)


def double_check(
    structural_model: dict,
    software_results: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    """Lance le double-check analytique M=qL²/8 / N_sum et retourne la liste d'anomalies."""
    parser = SafResultsParser()
    result = parser._run_double_check(structural_model, software_results)
    return [
        {
            "member_id": a.member_id,
            "check_type": a.check_type,
            "level": a.level.value,
            "message": a.message,
            "analytical_value": a.analytical_value,
            "software_value": a.software_value,
            "divergence_pct": a.divergence_pct,
            "is_anomaly": a.level == AnomalyLevel.ANOMALY,
        }
        for a in result.anomalies
    ]
