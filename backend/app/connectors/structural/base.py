"""Interface abstraite des connecteurs structure + modèles de résultats."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from app.connectors.thermic.base import ConnectorError, ConnectorTimeoutError

__all__ = [
    "ConnectorError",
    "ConnectorTimeoutError",
    "StructuralInputs",
    "StructuralConnector",
    "AnalysisResult",
    "MemberCheck",
    "StructuralAnomaly",
    "AnomalyLevel",
]


class AnomalyLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ANOMALY = "ANOMALY"


@dataclass
class StructuralAnomaly:
    """Anomalie détectée par le double-check analytique ou par le logiciel."""

    member_id: str
    check_type: str
    level: AnomalyLevel
    message: str
    analytical_value: float | None = None
    software_value: float | None = None
    divergence_pct: float | None = None


@dataclass
class MemberCheck:
    """Résultat de vérification d'un élément individuel."""

    member_id: str
    utilization_ratio: float  # taux de travail (1.0 = saturé)
    check_name: str           # "ULS_bending", "SLS_deflection", etc.
    compliant: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuralInputs:
    """Entrées d'une analyse structurelle."""

    ifc_path: Path | None           # optionnel : si fourni, extraction auto du modèle
    model_data: dict[str, Any] = field(default_factory=dict)  # sinon modèle JSON direct
    referentiel: str = "sia"         # sia | eurocode
    exposure_class: str = "XC2"
    consequence_class: str = "CC2"
    seismic_zone: str = "Z1b"
    material_default: str = "C30/37"
    timeout_seconds: int = 1800


@dataclass
class AnalysisResult:
    """Résultat d'une analyse structurelle."""

    compliant: bool
    max_utilization: float
    member_checks: list[MemberCheck] = field(default_factory=list)
    anomalies: list[StructuralAnomaly] = field(default_factory=list)
    engine_used: str = "unknown"
    computation_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    saf_file_path: Path | None = None
    note_md: str | None = None
    raw_output: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "compliant": self.compliant,
            "max_utilization": round(self.max_utilization, 3),
            "nb_checks": len(self.member_checks),
            "nb_anomalies": sum(1 for a in self.anomalies if a.level == AnomalyLevel.ANOMALY),
            "engine_used": self.engine_used,
            "computation_seconds": round(self.computation_seconds, 3),
            "warnings": self.warnings,
            "member_checks": [
                {
                    "member_id": m.member_id,
                    "check_name": m.check_name,
                    "utilization_ratio": round(m.utilization_ratio, 3),
                    "compliant": m.compliant,
                } for m in self.member_checks
            ],
            "anomalies": [
                {
                    "member_id": a.member_id,
                    "check_type": a.check_type,
                    "level": a.level.value,
                    "message": a.message,
                    "analytical_value": a.analytical_value,
                    "software_value": a.software_value,
                    "divergence_pct": a.divergence_pct,
                } for a in self.anomalies
            ],
            "saf_file_path": str(self.saf_file_path) if self.saf_file_path else None,
        }


class StructuralConnector(ABC):
    """Interface abstraite pour tout connecteur structure."""

    name: str = "abstract"

    @abstractmethod
    def validate_inputs(self, inputs: StructuralInputs) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, inputs: StructuralInputs) -> AnalysisResult:
        raise NotImplementedError
