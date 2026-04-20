"""Tests unitaires IDCCalculator - formule OCEN + correction DJU + classification."""
from __future__ import annotations

import pytest

from app.connectors.idc import (
    IDC_THRESHOLDS_KWH_M2_AN,
    IDCCalculator,
    IDCComputationInput,
    IDCStatus,
)
from app.connectors.idc.idc_calculator import IDCConsumption


def _cons(value: float, unit: str = "litre") -> IDCConsumption:
    return IDCConsumption(raw_value=value, raw_unit=unit)


class TestIDCCalculator:
    def test_mazout_5000l_500m2_gives_99_6(self) -> None:
        """5000 L × 9.96 kWh/L / 500 m² = 99.6 kWh/m²·an."""
        calc = IDCCalculator()
        result = calc.compute(IDCComputationInput(
            sre_m2=500.0, vector="mazout", affectation="logement_collectif",
            consumptions=[_cons(5000, "litre")], year=2024,
        ))
        assert abs(result.idc_normalized_kwh_m2_an - 99.6) < 0.1
        assert result.climate_correction_factor == 1.0
        assert result.total_energy_kwh == 49800.0

    def test_gaz_conversion_m3_pci(self) -> None:
        """1000 m³ gaz × 10.26 kWh/m³ = 10260 kWh."""
        calc = IDCCalculator()
        result = calc.compute(IDCComputationInput(
            sre_m2=200.0, vector="gaz", affectation="logement_collectif",
            consumptions=[_cons(1000, "m3")], year=2024,
        ))
        assert abs(result.total_energy_kwh - 10260.0) < 0.1
        assert abs(result.idc_raw_kwh_m2_an - 51.3) < 0.1

    def test_climate_correction_warm_year(self) -> None:
        """DJU année chaude (2500) → IDC normalisé > IDC brut, facteur ≈ 1.22."""
        calc = IDCCalculator()
        result = calc.compute(IDCComputationInput(
            sre_m2=1000.0, vector="chauffage_distance", affectation="logement_collectif",
            consumptions=[_cons(100_000, "kwh")], year=2024,
            dju_year_measured=2500.0,
        ))
        expected_factor = 3050.0 / 2500.0
        assert abs(result.climate_correction_factor - expected_factor) < 0.001
        assert result.idc_normalized_kwh_m2_an > result.idc_raw_kwh_m2_an

    def test_classification_ok_and_critique(self) -> None:
        calc = IDCCalculator()
        low = calc.compute(IDCComputationInput(
            sre_m2=1000.0, vector="chauffage_distance", affectation="logement_collectif",
            consumptions=[_cons(50_000, "kwh")], year=2024,
        ))
        assert low.classification.status == IDCStatus.OK

        high = calc.compute(IDCComputationInput(
            sre_m2=500.0, vector="mazout", affectation="logement_collectif",
            consumptions=[_cons(20_000, "litre")], year=2024,
        ))
        # 20'000 × 9.96 / 500 = 398.4 → > 300 seuil obligatoire → CRITIQUE
        assert high.classification.status == IDCStatus.CRITIQUE

    def test_zero_sre_raises(self) -> None:
        calc = IDCCalculator()
        with pytest.raises(ValueError, match="SRE"):
            calc.compute(IDCComputationInput(
                sre_m2=0.0, vector="gaz", affectation="logement_collectif",
                consumptions=[_cons(100, "m3")], year=2024,
            ))

    def test_unknown_vector_raises(self) -> None:
        calc = IDCCalculator()
        with pytest.raises(ValueError, match="Vecteur"):
            calc.compute(IDCComputationInput(
                sre_m2=100.0, vector="cold_fusion", affectation="logement_collectif",
                consumptions=[_cons(100)], year=2024,
            ))

    def test_thresholds_are_monotonically_increasing(self) -> None:
        """Les seuils OK < ATTENTION < ASSAINIR_RECO < ASSAINIR_OBLIGATOIRE."""
        for affectation, thresholds in IDC_THRESHOLDS_KWH_M2_AN.items():
            values = [thresholds[s] for s in (
                IDCStatus.OK, IDCStatus.ATTENTION,
                IDCStatus.ASSAINISSEMENT_RECOMMANDE, IDCStatus.ASSAINISSEMENT_OBLIGATOIRE,
            )]
            assert values == sorted(values), f"{affectation} : seuils non croissants {values}"
            assert all(v > 0 for v in values)
