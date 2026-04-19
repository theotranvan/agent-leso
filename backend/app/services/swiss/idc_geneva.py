"""Module IDC Genève - Indice de Dépense de Chaleur.

Fonctions :
- Extraction données de consommation depuis facture PDF chaufferie
- Conversion vers kWh selon vecteur énergétique
- Calcul IDC en MJ/m²/an (unité officielle genevoise)
- Génération formulaire PDF pré-rempli

Référence : LEn-GE / REn-GE - les seuils et formulaires exacts doivent être vérifiés
auprès de l'OCEN avant soumission.
"""
import logging
import re
from datetime import date
from io import BytesIO

from app.ch.cantons.geneve import idc_status
from app.ch.constants import VECTEURS_ENERGETIQUES
from app.services.pdf_extractor import extract_tables_from_pdf, extract_text_from_pdf

logger = logging.getLogger(__name__)


def convert_to_kwh(value: float, unit: str, vector: str) -> float:
    """Convertit une consommation en kWh selon l'unité source et le vecteur énergétique.

    Retourne 0 et logue une warning si la conversion n'est pas possible.
    """
    v = VECTEURS_ENERGETIQUES.get(vector, {})
    if unit == "kwh":
        return value
    if vector == "gaz" and unit in ("m3", "m³"):
        return value * v.get("pci_kwh_par_m3", 10.26)
    if vector == "mazout" and unit in ("litres", "l", "L"):
        return value * v.get("pci_kwh_par_litre", 9.96)
    if vector == "pellet" and unit in ("kg",):
        return value * v.get("pci_kwh_par_kg", 4.8)
    if vector == "buche" and unit in ("stere", "m3_stere"):
        return value * v.get("pci_kwh_par_m3_stere", 2000)
    logger.warning(f"Conversion inconnue : unit={unit}, vector={vector}")
    return 0


def kwh_to_mj(kwh: float) -> float:
    """1 kWh = 3.6 MJ."""
    return kwh * 3.6


def compute_idc_mj_m2_an(
    consumption_kwh: float,
    sre_m2: float,
    degree_days_period: float | None = None,
    degree_days_normal: float | None = None,
) -> dict:
    """Calcule l'IDC en MJ/m²/an.

    Si les degrés-jours sont fournis, applique la correction climatique :
    IDC_normalise = IDC_brut * (DJ_normal / DJ_periode)

    Retourne :
      - idc_brut_mj_m2 : IDC non corrigé
      - idc_normalise_mj_m2 : IDC corrigé du climat (si DJ fournis)
      - energy_mj : énergie totale en MJ
    """
    if sre_m2 <= 0:
        raise ValueError("SRE doit être strictement positive")

    energy_mj = kwh_to_mj(consumption_kwh)
    idc_brut = energy_mj / sre_m2

    result = {
        "idc_brut_mj_m2": round(idc_brut, 1),
        "idc_normalise_mj_m2": round(idc_brut, 1),
        "energy_mj": round(energy_mj, 0),
        "consumption_kwh": round(consumption_kwh, 0),
        "sre_m2": sre_m2,
    }

    if degree_days_period and degree_days_normal and degree_days_period > 0:
        correction = degree_days_normal / degree_days_period
        idc_norm = idc_brut * correction
        result["idc_normalise_mj_m2"] = round(idc_norm, 1)
        result["correction_climatique"] = round(correction, 3)

    return result


def extract_consumption_from_invoice_pdf(pdf_bytes: bytes, vector: str) -> dict:
    """Tente d'extraire une quantité consommée depuis une facture chaufferie (gaz, mazout).

    Retourne un dict {value, unit, period_start, period_end, confidence}.
    Cette extraction est best-effort ; l'utilisateur doit toujours valider les valeurs.
    """
    text, _ = extract_text_from_pdf(pdf_bytes)
    tables = extract_tables_from_pdf(pdf_bytes)

    # Patterns de reconnaissance
    # Gaz : "1234 m3" / "12'345 kWh" / "1.234,56 m³"
    # Mazout : "5000 litres" / "5'000 L" / "5000 l"
    result = {
        "value": None,
        "unit": None,
        "period_start": None,
        "period_end": None,
        "confidence": 0.0,
        "vector": vector,
    }

    # Normalisation nombres suisses (apostrophes, virgules)
    def to_float(s: str) -> float | None:
        try:
            cleaned = s.replace("'", "").replace(" ", "").replace(",", ".")
            return float(cleaned)
        except ValueError:
            return None

    lower = text.lower()

    if vector == "gaz":
        patterns = [
            r"([\d'.,\s]+)\s*(m3|m³)\s*(consomm|factur|total)",
            r"(consomm|factur|total)[^\d]{0,30}([\d'.,\s]+)\s*(m3|m³)",
        ]
        for pat in patterns:
            m = re.search(pat, lower, re.IGNORECASE)
            if m:
                num = to_float(m.group(1) if m.group(1) and m.group(1)[0].isdigit() else m.group(2))
                if num and 10 < num < 1_000_000:
                    result["value"] = num
                    result["unit"] = "m3"
                    result["confidence"] = 0.7
                    break
    elif vector == "mazout":
        patterns = [
            r"([\d'.,\s]+)\s*(litres?|l\.?)\s",
            r"([\d'.,\s]+)\s*l\s+livr",
        ]
        for pat in patterns:
            m = re.search(pat, lower, re.IGNORECASE)
            if m:
                num = to_float(m.group(1))
                if num and 100 < num < 200_000:
                    result["value"] = num
                    result["unit"] = "litres"
                    result["confidence"] = 0.6
                    break
    elif vector == "chauffage_distance":
        patterns = [
            r"([\d'.,\s]+)\s*kwh",
            r"([\d'.,\s]+)\s*mwh",
        ]
        for pat in patterns:
            m = re.search(pat, lower, re.IGNORECASE)
            if m:
                num = to_float(m.group(1))
                if num:
                    if "mwh" in m.group(0).lower():
                        num *= 1000
                    if 100 < num < 10_000_000:
                        result["value"] = num
                        result["unit"] = "kwh"
                        result["confidence"] = 0.8
                        break

    # Période : cherche "du 01.01.2025 au 31.12.2025" ou similaire
    period_pat = r"du\s+(\d{2})[./](\d{2})[./](\d{4})\s+au\s+(\d{2})[./](\d{2})[./](\d{4})"
    m = re.search(period_pat, text, re.IGNORECASE)
    if m:
        try:
            result["period_start"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            result["period_end"] = f"{m.group(6)}-{m.group(5)}-{m.group(4)}"
        except Exception:
            pass

    return result


def compute_annual_from_invoices(
    invoices_data: list[dict],
    sre_m2: float,
    vector: str,
    affectation: str = "logement_collectif",
) -> dict:
    """Aggrège plusieurs factures pour produire une consommation annuelle et calcule l'IDC.

    invoices_data = [{value, unit, period_start, period_end}, ...]
    """
    total_kwh = 0.0
    periods = []
    for inv in invoices_data:
        if not inv.get("value"):
            continue
        kwh = convert_to_kwh(inv["value"], inv.get("unit", "kwh"), vector)
        total_kwh += kwh
        if inv.get("period_start") and inv.get("period_end"):
            periods.append((inv["period_start"], inv["period_end"]))

    idc = compute_idc_mj_m2_an(total_kwh, sre_m2)
    status = idc_status(idc["idc_normalise_mj_m2"], affectation)

    return {
        **idc,
        "status": status,
        "vector": vector,
        "affectation": affectation,
        "nb_invoices": len(invoices_data),
        "periods": periods,
    }
