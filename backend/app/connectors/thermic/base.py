"""Interface abstraite des connecteurs thermiques + modèles de données partagés."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConnectorError(Exception):
    """Erreur générique d'un connecteur (input invalide, échec parsing, etc.)."""


class ConnectorTimeoutError(ConnectorError):
    """Timeout dépassé lors d'un appel externe (watched-folder, API, etc.)."""


class EnergyClass(str, Enum):
    """Classes énergétiques CECB A (meilleure) → G (pire)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


@dataclass(frozen=True)
class ThermicInputs:
    """Entrées d'une simulation thermique."""

    ifc_path: Path
    canton: str = "GE"
    affectation: str = "logement_collectif"
    operation_type: str = "neuf"
    standard: str = "sia_380_1"
    sre_m2: float | None = None
    heating_vector: str = "gaz"
    hypotheses: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 1800


@dataclass
class SimulationResult:
    """Résultat standard de toute simulation thermique."""

    qh_kwh_m2_an: float
    ep_kwh_m2_an: float
    sre_m2: float
    idc_kwh_m2_an: float | None = None
    qh_limite_kwh_m2_an: float | None = None
    energy_class: EnergyClass | None = None
    compliant: bool | None = None
    engine_used: str = "unknown"
    computation_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    raw_output: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "qh_kwh_m2_an": round(self.qh_kwh_m2_an, 2),
            "ep_kwh_m2_an": round(self.ep_kwh_m2_an, 2),
            "sre_m2": round(self.sre_m2, 2),
            "idc_kwh_m2_an": round(self.idc_kwh_m2_an, 2) if self.idc_kwh_m2_an is not None else None,
            "qh_limite_kwh_m2_an": round(self.qh_limite_kwh_m2_an, 2) if self.qh_limite_kwh_m2_an is not None else None,
            "energy_class": self.energy_class.value if self.energy_class else None,
            "compliant": self.compliant,
            "engine_used": self.engine_used,
            "computation_seconds": round(self.computation_seconds, 3),
            "warnings": self.warnings,
            "raw_output": self.raw_output,
        }


class ThermicConnector(ABC):
    """Interface abstraite pour tout connecteur thermique."""

    name: str = "abstract"

    @abstractmethod
    def validate_inputs(self, inputs: ThermicInputs) -> list[str]:
        """Valide les entrées. Retourne warnings. Lève ConnectorError si inexploitable."""
        raise NotImplementedError

    @abstractmethod
    def simulate(self, inputs: ThermicInputs) -> SimulationResult:
        """Exécute la simulation et retourne un SimulationResult.

        Lève ConnectorError / ConnectorTimeoutError.
        """
        raise NotImplementedError

    def supports_canton(self, canton: str) -> bool:
        return True


# Valeurs limites SIA 380/1 (kWh/m²·an) - références uniquement
SIA_380_1_LIMITES_QH_KWH_M2_AN: dict[str, float] = {
    "logement_individuel": 61.0,
    "logement_collectif": 44.0,
    "administration": 39.0,
    "ecole": 39.0,
    "commerce": 39.0,
    "restauration": 61.0,
    "hopital": 50.0,
    "industriel": 50.0,
    "depot": 78.0,
    "sport": 78.0,
    "piscine_couverte": 170.0,
    "lieu_rassemblement": 50.0,
}

SIA_380_1_DEFAULT_U_VALUES: dict[str, float] = {
    "wall_external": 0.17,
    "wall_ground": 0.25,
    "roof": 0.17,
    "slab_ground": 0.25,
    "window": 1.0,
    "door": 1.2,
}


def limite_qh_for_affectation(affectation: str) -> float | None:
    return SIA_380_1_LIMITES_QH_KWH_M2_AN.get(affectation)


def default_u_value(element_type: str) -> float:
    return SIA_380_1_DEFAULT_U_VALUES.get(element_type, 0.25)


def qh_to_energy_class(qh_kwh_m2_an: float) -> EnergyClass:
    """Conversion indicative Qh→classe CECB pour logement collectif.

    Seuils indicatifs basés sur les valeurs limites SIA 380/1 neuf et existant.
    À valider avec grille CECB officielle en vigueur.
    """
    if qh_kwh_m2_an <= 25:
        return EnergyClass.A
    if qh_kwh_m2_an <= 50:
        return EnergyClass.B
    if qh_kwh_m2_an <= 80:
        return EnergyClass.C
    if qh_kwh_m2_an <= 120:
        return EnergyClass.D
    if qh_kwh_m2_an <= 170:
        return EnergyClass.E
    if qh_kwh_m2_an <= 230:
        return EnergyClass.F
    return EnergyClass.G
