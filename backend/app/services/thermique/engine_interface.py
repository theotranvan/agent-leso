"""Interface abstraite pour moteurs thermiques SIA 380/1.

Permet de brancher plusieurs implémentations :
- LesosaiStubEngine : dummy qui produit du JSON (V2)
- LesosaiFileEngine : génération fichier XML Lesosai pour saisie opérateur
- LesosaiApiEngine : appel API direct (V3, quand E4tech confirme)
- InternalEngine : moteur alternatif (V3)
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class ThermalEngineResult:
    """Structure standard des résultats thermiques."""
    def __init__(
        self,
        qh_mj_m2_an: float,            # besoin de chauffage
        qww_mj_m2_an: float,           # besoin ECS
        e_mj_m2_an: float,             # énergie primaire totale
        qh_limite_mj_m2_an: float | None = None,
        compliant: bool | None = None,
        warnings: list[str] | None = None,
        engine_used: str = "unknown",
        raw_results: dict | None = None,
    ):
        self.qh_mj_m2_an = qh_mj_m2_an
        self.qww_mj_m2_an = qww_mj_m2_an
        self.e_mj_m2_an = e_mj_m2_an
        self.qh_limite_mj_m2_an = qh_limite_mj_m2_an
        self.compliant = compliant
        self.warnings = warnings or []
        self.engine_used = engine_used
        self.raw_results = raw_results or {}

    def to_dict(self) -> dict:
        return {
            "qh_mj_m2_an": self.qh_mj_m2_an,
            "qww_mj_m2_an": self.qww_mj_m2_an,
            "e_mj_m2_an": self.e_mj_m2_an,
            "qh_limite_mj_m2_an": self.qh_limite_mj_m2_an,
            "compliant": self.compliant,
            "warnings": self.warnings,
            "engine_used": self.engine_used,
            "raw_results": self.raw_results,
        }


class ThermalEngine(ABC):
    """Interface commune pour tous les moteurs thermiques."""

    name: str = "abstract"

    @abstractmethod
    async def prepare_model(self, thermal_model: dict) -> dict:
        """Prépare/valide le modèle avant envoi au moteur.
        Retourne un dict de payload prêt à envoyer (+ warnings éventuels)."""
        ...

    @abstractmethod
    async def submit(self, payload: dict) -> str:
        """Envoie le modèle au moteur. Retourne un identifiant de job ou le path du fichier produit."""
        ...

    @abstractmethod
    async def fetch_results(self, job_id: str) -> ThermalEngineResult | None:
        """Récupère les résultats. Retourne None si pas encore prêt (pour moteurs asynchrones)."""
        ...

    @abstractmethod
    def is_synchronous(self) -> bool:
        """True si submit retourne directement les résultats (cas du stub).
        False si les résultats nécessitent une saisie externe (cas fichier Lesosai)."""
        ...
