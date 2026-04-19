"""Moteur Lesosai STUB - implémentation dummy pour développement / tests.

Calcule un IDC approximatif SIA 380/1 selon une méthode simplifiée
(pas équivalente SIA 380/1 officielle, à utiliser UNIQUEMENT pour les tests
et pour ne pas bloquer le reste de la plateforme).

Ce stub est REMPLACÉ par LesosaiFileEngine ou LesosaiApiEngine en production.
"""
import logging
from datetime import datetime

from app.services.thermique.engine_interface import ThermalEngine, ThermalEngineResult

logger = logging.getLogger(__name__)


# Valeurs limites SIA 380/1 indicatives par affectation (MJ/m²/an)
# À affiner selon l'édition en vigueur
VALEURS_LIMITES_QH_INDICATIVES = {
    "logement_collectif": 160,
    "logement_individuel": 220,
    "administration": 140,
    "ecole": 140,
    "commerce": 140,
    "restauration": 220,
    "industriel": 180,
    "depot": 280,
    "sport": 280,
    "hopital": 180,
}


class LesosaiStubEngine(ThermalEngine):
    """Moteur dummy - NON équivalent à un calcul SIA 380/1 officiel.

    Permet de :
    - Développer le reste de la plateforme sans dépendre de Lesosai
    - Fournir des estimations rapides indicatives en phase d'avant-projet
    - Tester le pipeline end-to-end

    ATTENTION : ne JAMAIS utiliser pour produire un justificatif officiel.
    """

    name = "lesosai_stub"

    async def prepare_model(self, thermal_model: dict) -> dict:
        """Vérifie les champs minimums."""
        warnings = []

        zones = thermal_model.get("zones") or []
        walls = thermal_model.get("walls") or []
        openings = thermal_model.get("openings") or []
        systems = thermal_model.get("systems") or {}

        if not zones:
            warnings.append("Aucune zone thermique définie")
        if not walls:
            warnings.append("Aucune paroi définie")

        total_area = sum(z.get("area", 0) for z in zones)
        if total_area <= 0:
            warnings.append("Surface totale de zones nulle")

        return {
            "model": thermal_model,
            "warnings": warnings,
            "sre_total_m2": total_area,
            "prepared_at": datetime.utcnow().isoformat(),
        }

    async def submit(self, payload: dict) -> str:
        """Retourne immédiatement un faux job_id. Le calcul est synchrone."""
        return f"stub_{datetime.utcnow().timestamp()}"

    async def fetch_results(self, job_id: str) -> ThermalEngineResult | None:
        """Pour le stub, on ne garde pas d'état : le calcul se fait dans compute()."""
        return None

    def is_synchronous(self) -> bool:
        return True

    async def compute(self, thermal_model: dict) -> ThermalEngineResult:
        """Calcul simplifié indicatif.

        Méthode très approximative :
          Qh ≈ (somme(U*A) des parois * DJ * 24 / 1000) / SRE + contribution pertes
          On ne prend PAS en compte les apports solaires ni internes correctement.
        """
        prep = await self.prepare_model(thermal_model)
        payload_warnings = prep["warnings"]
        sre = max(prep["sre_total_m2"], 1.0)

        # Somme U*A (déperditions conductives)
        u_a_total = 0.0
        for wall in thermal_model.get("walls", []):
            u = wall.get("u_value") or 0.5
            area = wall.get("area") or 0
            u_a_total += u * area
        for opening in thermal_model.get("openings", []):
            u = opening.get("u_value") or 1.3
            area = opening.get("area") or 0
            u_a_total += u * area

        # Degrés-jours indicatifs (base 20-12°C)
        climate = thermal_model.get("climate", {})
        dj = climate.get("dj_20_12", 3100)  # défaut Genève

        # Pertes annuelles en kWh
        pertes_kwh = u_a_total * dj * 24 / 1000
        qh_kwh_m2 = pertes_kwh / sre
        qh_mj_m2 = qh_kwh_m2 * 3.6

        # ECS forfaitaire selon affectation
        affectation = thermal_model.get("affectation", "logement_collectif")
        qww_forfait = {
            "logement_collectif": 75,
            "logement_individuel": 50,
            "administration": 25,
            "ecole": 30,
            "commerce": 25,
        }.get(affectation, 50)

        # Énergie primaire (facteur indicatif 1.5 - neutre)
        e_mj = (qh_mj_m2 + qww_forfait) * 1.5

        qh_limite = VALEURS_LIMITES_QH_INDICATIVES.get(affectation)
        compliant = None if qh_limite is None else qh_mj_m2 <= qh_limite

        warnings = list(payload_warnings)
        warnings.append(
            "CALCUL INDICATIF - Moteur stub non équivalent SIA 380/1. "
            "Ne pas utiliser pour un justificatif officiel."
        )
        if qh_mj_m2 > 500:
            warnings.append("Qh > 500 MJ/m²/an - valeurs d'entrée probablement incorrectes")

        return ThermalEngineResult(
            qh_mj_m2_an=round(qh_mj_m2, 1),
            qww_mj_m2_an=round(qww_forfait, 1),
            e_mj_m2_an=round(e_mj, 1),
            qh_limite_mj_m2_an=qh_limite,
            compliant=compliant,
            warnings=warnings,
            engine_used=self.name,
            raw_results={
                "u_a_total_W_K": round(u_a_total, 1),
                "dj_20_12": dj,
                "sre_m2": sre,
                "pertes_annuelles_kwh": round(pertes_kwh, 0),
            },
        )
