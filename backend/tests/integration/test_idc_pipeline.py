"""Pipeline IDC bout-en-bout : facture PDF → extraction → calcul → classification."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.connectors.idc import IDCCalculator, IDCComputationInput
from app.connectors.idc.facture_extractor import FactureExtractor
from app.connectors.idc.idc_calculator import IDCConsumption
from app.connectors.idc.ocen_form_generator import OCENFormGenerator, OCENFormInput


class TestIDCPipeline:
    def test_full_pipeline_pdf_to_classification(self, temp_facture_mazout_pdf: Path) -> None:
        """Facture PDF → extraction → calcul IDC → classification."""
        extractor = FactureExtractor(enable_claude_fallback=False)
        extraction = extractor.extract(temp_facture_mazout_pdf.read_bytes(), vector="mazout")
        assert extraction.value is not None
        assert extraction.unit == "litre"

        calc = IDCCalculator()
        result = calc.compute(IDCComputationInput(
            sre_m2=500.0,
            vector="mazout",
            affectation="logement_collectif",
            consumptions=[IDCConsumption(
                raw_value=extraction.value,
                raw_unit=extraction.unit,
                period_start=extraction.period_start,
                period_end=extraction.period_end,
            )],
            year=2024,
        ))
        # 5250 L × 9.96 / 500 = ~104.6 kWh/m²·an
        assert 95 <= result.idc_normalized_kwh_m2_an <= 115
        assert result.classification.status.value in ("OK", "ATTENTION")

    def test_multi_invoices_aggregation(self) -> None:
        """Agrégation de 3 factures partielles → IDC annuel cohérent."""
        calc = IDCCalculator()
        consumptions = [
            IDCConsumption(2000, "litre", period_start=date(2024, 1, 1), period_end=date(2024, 4, 30)),
            IDCConsumption(1500, "litre", period_start=date(2024, 5, 1), period_end=date(2024, 8, 31)),
            IDCConsumption(2500, "litre", period_start=date(2024, 9, 1), period_end=date(2024, 12, 31)),
        ]
        result = calc.compute(IDCComputationInput(
            sre_m2=800.0, vector="mazout", affectation="logement_collectif",
            consumptions=consumptions, year=2024,
        ))

        # Total = 6000 L × 9.96 / 800 = 74.7 kWh/m²·an
        assert abs(result.idc_normalized_kwh_m2_an - 74.7) < 0.5
        assert result.details["nb_consumptions"] == 3.0

    def test_ocen_form_pdf_generation(self) -> None:
        """Génération PDF OCEN à partir d'un résultat IDC réel."""
        calc = IDCCalculator()
        idc = calc.compute(IDCComputationInput(
            sre_m2=1250.0,
            vector="gaz",
            affectation="logement_collectif",
            consumptions=[IDCConsumption(8000, "m3")],
            year=2024,
        ))

        form_input = OCENFormInput(
            egid="1234567",
            address="Rue du Test 42",
            postal_code="1207",
            city="Genève",
            sre_m2=1250.0,
            heating_vector="gaz",
            building_year=1985,
            nb_logements=18,
            regie_name="Régie Test SA",
            regie_email="test@regie.ch",
        )

        gen = OCENFormGenerator()
        try:
            pdf_bytes = gen.generate(form_input, idc)
        except RuntimeError as exc:
            if "WeasyPrint" in str(exc):
                pytest.skip("WeasyPrint non installé dans cet env de test")
            raise

        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 5000
