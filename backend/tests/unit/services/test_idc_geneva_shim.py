"""Tests du shim IDC Genève — vérifie que la correction climatique DJU est bien
appliquée par la fonction réellement utilisée par la route /declarations.

Régression historique : la route ne transmettait pas le DJU de l'année, la
correction restait donc figée à 1.0 (IDC brut == IDC normalisé).
"""
from __future__ import annotations

from app.services.swiss.idc_geneva import compute_annual_from_invoices

# 100 000 kWh sur 1000 m² → IDC brut = 100 kWh/m²·an = 360 MJ/m²·an
_INVOICES = [{"value": 100_000, "unit": "kwh", "period_start": "2023-01-01", "period_end": "2023-12-31"}]


def test_sans_dju_aucune_correction() -> None:
    r = compute_annual_from_invoices(_INVOICES, sre_m2=1000.0, vector="chauffage_distance")
    assert r["correction_factor"] == 1.0
    assert r["idc_raw_kwh_m2_an"] == r["idc_kwh_m2_an"]


def test_annee_froide_corrige_a_la_baisse() -> None:
    # DJU année (3500) > DJU normal Genève (3050) → correction < 1 → IDC normalisé < brut.
    r = compute_annual_from_invoices(
        _INVOICES, sre_m2=1000.0, vector="chauffage_distance", year=2023, dju_year=3500.0,
    )
    assert r["correction_factor"] < 1.0
    assert abs(r["correction_factor"] - 3050.0 / 3500.0) < 0.001
    assert r["idc_kwh_m2_an"] < r["idc_raw_kwh_m2_an"]


def test_annee_douce_corrige_a_la_hausse() -> None:
    # DJU année (2600) < DJU normal → correction > 1 → IDC normalisé > brut.
    r = compute_annual_from_invoices(
        _INVOICES, sre_m2=1000.0, vector="chauffage_distance", year=2022, dju_year=2600.0,
    )
    assert r["correction_factor"] > 1.0
    assert r["idc_kwh_m2_an"] > r["idc_raw_kwh_m2_an"]
