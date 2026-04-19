"""Calculateur IDC Genève (Indice de Dépense de Chaleur).

## Formule officielle OCEN

L'IDC exprime la consommation annuelle de chaleur pour chauffage et ECS,
ramenée à la Surface de Référence Énergétique (SRE) et corrigée du climat :

    IDC_normalisé = (E_mesurée × DJU_normal / DJU_année_mesure) / SRE

où :
- E_mesurée : énergie consommée pour chauffage + ECS sur la période (kWh)
- DJU_normal : degrés-jours de la station météo normale (base 20/12°C)
- DJU_année_mesure : DJU effectifs de l'année de mesure
- SRE : Surface de Référence Énergétique (m²)

Unité : **kWh/m²·an** (l'OCEN utilise aussi MJ/m²·an = kWh × 3.6).

## DJU Genève-Cointrin
Station de référence officielle pour le canton de Genève.
Valeur normale base 20/12 : 3050 DJU/an
(Source : MétéoSuisse / SIA 2028)

## Seuils 2024

Les seuils diffèrent selon l'affectation. Les valeurs ci-dessous sont indicatives
et doivent être confirmées auprès de l'OCEN pour chaque exercice réglementaire.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Final

logger = logging.getLogger(__name__)

# Conversions d'unités
KWH_PER_MJ: Final[float] = 1.0 / 3.6
MJ_PER_KWH: Final[float] = 3.6

# DJU normaux base 20/12°C (SIA 2028)
DJU_NORMAL_GENEVA_COINTRIN: Final[float] = 3050.0  # SOURCE: SIA 2028 station Genève-Cointrin

# PCI par vecteur énergétique (kWh par unité)
VECTEUR_PCI: Final[dict[str, tuple[float, str]]] = {
    "gaz": (10.26, "m3"),            # SOURCE: SSIGE - gaz naturel
    "mazout": (9.96, "litre"),       # SOURCE: PCI mazout EL selon OFEN
    "pellet": (4.8, "kg"),           # SOURCE: OFEN - granulés bois
    "buche": (2000.0, "stere"),      # SOURCE: OFEN - bûches feuillues
    "chauffage_distance": (1.0, "kwh"),
    "electrique": (1.0, "kwh"),
    "pac_air_eau": (1.0, "kwh"),
    "pac_sol_eau": (1.0, "kwh"),
    "solaire_thermique": (1.0, "kwh"),
}


class IDCStatus(str, Enum):
    """Classification IDC - 5 niveaux réglementaires."""

    OK = "OK"
    ATTENTION = "ATTENTION"
    ASSAINISSEMENT_RECOMMANDE = "ASSAINISSEMENT_RECOMMANDE"
    ASSAINISSEMENT_OBLIGATOIRE = "ASSAINISSEMENT_OBLIGATOIRE"
    CRITIQUE = "CRITIQUE"


# SOURCE: OCEN GE 2024 — À CONFIRMER
# Seuils indicatifs en kWh/m²·an (tels qu'interprétés depuis la doc publique).
# Les valeurs exactes peuvent varier selon l'année de construction, le type
# d'enveloppe et l'affectation précise. Toujours vérifier le référentiel OCEN
# en vigueur avant soumission officielle.
IDC_THRESHOLDS_KWH_M2_AN: Final[dict[str, dict[IDCStatus, float]]] = {
    "logement_collectif": {
        IDCStatus.OK: 125.0,
        IDCStatus.ATTENTION: 167.0,
        IDCStatus.ASSAINISSEMENT_RECOMMANDE: 222.0,
        IDCStatus.ASSAINISSEMENT_OBLIGATOIRE: 300.0,
    },
    "logement_individuel": {
        IDCStatus.OK: 139.0,
        IDCStatus.ATTENTION: 181.0,
        IDCStatus.ASSAINISSEMENT_RECOMMANDE: 236.0,
        IDCStatus.ASSAINISSEMENT_OBLIGATOIRE: 320.0,
    },
    "administration": {
        IDCStatus.OK: 97.0,
        IDCStatus.ATTENTION: 139.0,
        IDCStatus.ASSAINISSEMENT_RECOMMANDE: 194.0,
        IDCStatus.ASSAINISSEMENT_OBLIGATOIRE: 267.0,
    },
    "commerce": {
        IDCStatus.OK: 111.0,
        IDCStatus.ATTENTION: 153.0,
        IDCStatus.ASSAINISSEMENT_RECOMMANDE: 208.0,
        IDCStatus.ASSAINISSEMENT_OBLIGATOIRE: 278.0,
    },
    "industriel": {
        IDCStatus.OK: 125.0,
        IDCStatus.ATTENTION: 181.0,
        IDCStatus.ASSAINISSEMENT_RECOMMANDE: 250.0,
        IDCStatus.ASSAINISSEMENT_OBLIGATOIRE: 333.0,
    },
}


@dataclass
class IDCClassification:
    """Résultat du classement d'un IDC."""

    status: IDCStatus
    label: str
    action_required: str
    color: str


@dataclass(frozen=True)
class IDCConsumption:
    """Une consommation mesurée (ex: une facture)."""

    raw_value: float
    raw_unit: str       # "m3", "litre", "kwh", "kg", "stere"
    period_start: date | None = None
    period_end: date | None = None
    source_document_id: str | None = None


@dataclass(frozen=True)
class IDCComputationInput:
    """Entrées pour le calcul IDC annuel d'un bâtiment."""

    sre_m2: float
    vector: str
    affectation: str
    consumptions: list[IDCConsumption]
    year: int
    dju_year_measured: float | None = None  # DJU réels de l'année (si connus)


@dataclass
class IDCComputationResult:
    """Résultat complet du calcul IDC."""

    idc_raw_kwh_m2_an: float
    idc_normalized_kwh_m2_an: float
    idc_raw_mj_m2_an: float
    idc_normalized_mj_m2_an: float
    total_energy_kwh: float
    climate_correction_factor: float
    sre_m2: float
    year: int
    classification: IDCClassification
    warnings: list[str] = field(default_factory=list)
    details: dict[str, float] = field(default_factory=dict)


class IDCCalculator:
    """Calculateur IDC complet avec correction DJU + classification."""

    def __init__(self, dju_normal: float = DJU_NORMAL_GENEVA_COINTRIN) -> None:
        self.dju_normal = dju_normal

    def compute(self, inputs: IDCComputationInput) -> IDCComputationResult:
        """Calcule l'IDC annuel d'un bâtiment.

        Lève ValueError si entrées invalides.
        """
        if inputs.sre_m2 <= 0:
            raise ValueError(f"SRE doit être > 0, reçu {inputs.sre_m2}")
        if not inputs.consumptions:
            raise ValueError("Aucune consommation fournie")
        if inputs.vector not in VECTEUR_PCI:
            raise ValueError(
                f"Vecteur énergétique inconnu : {inputs.vector} "
                f"(supportés : {list(VECTEUR_PCI.keys())})"
            )

        warnings: list[str] = []

        # 1. Conversion de chaque consommation en kWh + somme
        total_kwh = 0.0
        pci, expected_unit = VECTEUR_PCI[inputs.vector]
        for cons in inputs.consumptions:
            if cons.raw_value <= 0:
                warnings.append(f"Consommation nulle ou négative ignorée : {cons.raw_value}")
                continue
            kwh = self._to_kwh(cons.raw_value, cons.raw_unit, inputs.vector, warnings)
            total_kwh += kwh

        if total_kwh <= 0:
            raise ValueError("Énergie totale calculée est nulle")

        # 2. IDC brut
        idc_raw_kwh = total_kwh / inputs.sre_m2

        # 3. Correction climatique
        dju_year = inputs.dju_year_measured if inputs.dju_year_measured else self.dju_normal
        if dju_year <= 0:
            raise ValueError(f"DJU année invalide : {dju_year}")
        correction = self.dju_normal / dju_year
        idc_normalized_kwh = idc_raw_kwh * correction

        if correction < 0.8 or correction > 1.3:
            warnings.append(
                f"Correction climatique inhabituelle ({correction:.3f}) - "
                f"vérifier les DJU de l'année {inputs.year}"
            )

        # 4. Classification
        classification = self._classify(idc_normalized_kwh, inputs.affectation, warnings)

        logger.info(
            "IDC calculé : %.1f kWh/m²·an (classification %s) - SRE=%.1fm², correction=%.3f",
            idc_normalized_kwh, classification.status.value, inputs.sre_m2, correction,
        )

        return IDCComputationResult(
            idc_raw_kwh_m2_an=round(idc_raw_kwh, 2),
            idc_normalized_kwh_m2_an=round(idc_normalized_kwh, 2),
            idc_raw_mj_m2_an=round(idc_raw_kwh * MJ_PER_KWH, 2),
            idc_normalized_mj_m2_an=round(idc_normalized_kwh * MJ_PER_KWH, 2),
            total_energy_kwh=round(total_kwh, 1),
            climate_correction_factor=round(correction, 4),
            sre_m2=inputs.sre_m2,
            year=inputs.year,
            classification=classification,
            warnings=warnings,
            details={
                "dju_normal": self.dju_normal,
                "dju_year_measured": dju_year,
                "nb_consumptions": float(len(inputs.consumptions)),
                "vector_pci_kwh": pci,
            },
        )

    def _to_kwh(self, value: float, unit: str, vector: str, warnings: list[str]) -> float:
        """Convertit une quantité en kWh selon unité et vecteur."""
        unit_norm = unit.lower().replace("³", "3").replace("²", "2").strip()
        pci, expected = VECTEUR_PCI[vector]

        if unit_norm in ("kwh", "kilowatt heure", "kilowattheure"):
            return value
        if unit_norm in ("mwh", "megawatt heure"):
            return value * 1000.0
        if unit_norm in ("mj", "megajoule"):
            return value * KWH_PER_MJ
        if unit_norm in ("gj", "gigajoule"):
            return value * 1000.0 * KWH_PER_MJ

        # Unités spécifiques au vecteur
        if vector == "gaz" and unit_norm in ("m3", "m^3"):
            return value * pci
        if vector == "mazout" and unit_norm in ("l", "litre", "litres"):
            return value * pci
        if vector == "pellet" and unit_norm in ("kg",):
            return value * pci
        if vector == "buche" and unit_norm in ("stere", "steres", "m3_stere"):
            return value * pci

        warnings.append(
            f"Conversion inconnue {unit}→kWh pour vecteur {vector} "
            f"(attendu : {expected}). Valeur considérée comme déjà en kWh."
        )
        return value

    def _classify(
        self,
        idc_kwh: float,
        affectation: str,
        warnings: list[str],
    ) -> IDCClassification:
        thresholds = IDC_THRESHOLDS_KWH_M2_AN.get(affectation)
        if thresholds is None:
            warnings.append(
                f"Affectation '{affectation}' sans seuils spécifiques - "
                f"fallback sur logement_collectif"
            )
            thresholds = IDC_THRESHOLDS_KWH_M2_AN["logement_collectif"]

        if idc_kwh <= thresholds[IDCStatus.OK]:
            return IDCClassification(
                status=IDCStatus.OK,
                label="Dans la cible",
                action_required="Aucune action réglementaire requise",
                color="#10B981",
            )
        if idc_kwh <= thresholds[IDCStatus.ATTENTION]:
            return IDCClassification(
                status=IDCStatus.ATTENTION,
                label="Surconsommation modérée",
                action_required="Audit énergétique recommandé",
                color="#F59E0B",
            )
        if idc_kwh <= thresholds[IDCStatus.ASSAINISSEMENT_RECOMMANDE]:
            return IDCClassification(
                status=IDCStatus.ASSAINISSEMENT_RECOMMANDE,
                label="Surconsommation marquée",
                action_required="Plan d'assainissement énergétique à étudier",
                color="#F97316",
            )
        if idc_kwh <= thresholds[IDCStatus.ASSAINISSEMENT_OBLIGATOIRE]:
            return IDCClassification(
                status=IDCStatus.ASSAINISSEMENT_OBLIGATOIRE,
                label="Très forte surconsommation",
                action_required="Assainissement à planifier (obligations LEn-GE à vérifier)",
                color="#EF4444",
            )
        return IDCClassification(
            status=IDCStatus.CRITIQUE,
            label="Consommation critique",
            action_required="Action corrective urgente requise",
            color="#991B1B",
        )
