"""Shim IDC Genève V2 → délègue aux connectors V3 (idc_calculator + facture_extractor).

Maintient les 5 signatures publiques utilisées par routes/idc.py et par l'agent genève.
"""
from __future__ import annotations

import logging
from datetime import date
from io import BytesIO
from typing import Any

from app.connectors.idc.facture_extractor import FactureExtractor
from app.connectors.idc.idc_calculator import (
    DJU_NORMAL_GENEVA_COINTRIN,
    IDC_THRESHOLDS_KWH_M2_AN,
    IDCCalculator,
    IDCComputationInput,
    IDCConsumption,
    IDCStatus,
    MJ_PER_KWH,
    VECTEUR_PCI,
)

logger = logging.getLogger(__name__)


# ----- Conversions unitaires (compat V2) -----

def convert_to_kwh(value: float, unit: str, vector: str) -> float:
    """Convertit une consommation vers kWh selon unité/vecteur.

    Compat V2 : retourne 0 et logue si non convertible (au lieu de raise).
    """
    if value <= 0 or vector not in VECTEUR_PCI:
        logger.warning("convert_to_kwh : input invalide (value=%s, vector=%s)", value, vector)
        return 0.0
    calc = IDCCalculator()
    warnings: list[str] = []
    kwh = calc._to_kwh(value, unit, vector, warnings)
    if warnings:
        logger.warning("convert_to_kwh warnings : %s", warnings)
    return kwh


def kwh_to_mj(kwh: float) -> float:
    """Conversion utilitaire kWh → MJ."""
    return round(kwh * MJ_PER_KWH, 2)


# ----- Calcul IDC normalisé (compat V2) -----

def compute_idc_mj_m2_an(
    consumption_kwh: float,
    sre_m2: float,
    dju_year: float | None = None,
    dju_normal: float = DJU_NORMAL_GENEVA_COINTRIN,
) -> dict[str, Any]:
    """Calcul simple IDC avec correction DJU.

    Retourne un dict V2-compatible :
        {idc_mj_m2_an, idc_kwh_m2_an, correction_factor, status, ...}
    """
    if sre_m2 <= 0:
        raise ValueError("SRE doit être > 0")
    if consumption_kwh < 0:
        raise ValueError("consommation négative")

    idc_raw_kwh = consumption_kwh / sre_m2
    factor = (dju_normal / dju_year) if (dju_year and dju_year > 0) else 1.0
    idc_norm_kwh = idc_raw_kwh * factor

    # Statut simplifié via seuils logement collectif par défaut
    thresholds = IDC_THRESHOLDS_KWH_M2_AN["logement_collectif"]
    if idc_norm_kwh <= thresholds[IDCStatus.OK]:
        status = "OK"
    elif idc_norm_kwh <= thresholds[IDCStatus.ATTENTION]:
        status = "ATTENTION"
    elif idc_norm_kwh <= thresholds[IDCStatus.ASSAINISSEMENT_RECOMMANDE]:
        status = "ASSAINISSEMENT_RECOMMANDE"
    elif idc_norm_kwh <= thresholds[IDCStatus.ASSAINISSEMENT_OBLIGATOIRE]:
        status = "ASSAINISSEMENT_OBLIGATOIRE"
    else:
        status = "CRITIQUE"

    return {
        "idc_kwh_m2_an": round(idc_norm_kwh, 2),
        "idc_mj_m2_an": round(idc_norm_kwh * MJ_PER_KWH, 2),
        "idc_raw_kwh_m2_an": round(idc_raw_kwh, 2),
        "correction_factor": round(factor, 4),
        "dju_normal": dju_normal,
        "dju_year": dju_year,
        "status": status,
    }


# ----- Extraction facture PDF (compat V2) -----

def extract_consumption_from_invoice_pdf(pdf_bytes: bytes, vector: str) -> dict:
    """Extrait la consommation depuis un PDF de facture.

    Compat V2 : retourne un dict plat.
    """
    extractor = FactureExtractor(enable_claude_fallback=True)
    result = extractor.extract(pdf_bytes, vector=vector)
    return {
        "value": result.value,
        "unit": result.unit,
        "period_start": result.period_start.isoformat() if result.period_start else None,
        "period_end": result.period_end.isoformat() if result.period_end else None,
        "confidence": round(result.confidence, 3),
        "extraction_method": result.extraction_method,
        "warnings": result.warnings,
    }


# ----- Calcul annuel depuis liste factures (compat V2) -----

def compute_annual_from_invoices(
    invoices: list[dict[str, Any]],
    sre_m2: float,
    vector: str,
    affectation: str = "logement_collectif",
    year: int | None = None,
    dju_year: float | None = None,
) -> dict[str, Any]:
    """Agrège plusieurs factures et calcule l'IDC annuel.

    `invoices` : liste de dicts {value, unit, period_start?, period_end?, source_doc_id?}
    """
    if not invoices:
        raise ValueError("Aucune facture fournie")

    consumptions: list[IDCConsumption] = []
    for inv in invoices:
        ps = inv.get("period_start")
        pe = inv.get("period_end")
        consumptions.append(IDCConsumption(
            raw_value=float(inv.get("value", 0)),
            raw_unit=str(inv.get("unit", "kwh")),
            period_start=date.fromisoformat(ps) if isinstance(ps, str) else None,
            period_end=date.fromisoformat(pe) if isinstance(pe, str) else None,
            source_document_id=inv.get("source_doc_id"),
        ))

    calc = IDCCalculator()
    result = calc.compute(IDCComputationInput(
        sre_m2=sre_m2,
        vector=vector,
        affectation=affectation,
        consumptions=consumptions,
        year=year or date.today().year,
        dju_year_measured=dju_year,
    ))

    return {
        "idc_kwh_m2_an": result.idc_normalized_kwh_m2_an,
        "idc_mj_m2_an": result.idc_normalized_mj_m2_an,
        "idc_raw_kwh_m2_an": result.idc_raw_kwh_m2_an,
        "total_energy_kwh": result.total_energy_kwh,
        "correction_factor": result.climate_correction_factor,
        "status": result.classification.status.value,
        "classification_label": result.classification.label,
        "action_required": result.classification.action_required,
        "warnings": result.warnings,
        "nb_factures": len(invoices),
    }
