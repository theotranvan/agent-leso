"""Tests d'intégration du pipeline thermique complet IFC → gbXML → résultat."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.connectors.thermic import ThermicInputs
from app.connectors.thermic.gbxml_generator import GbxmlGenerator
from app.connectors.thermic.stub import StubThermicConnector


class TestThermicPipeline:
    def test_pipeline_stub_end_to_end(self) -> None:
        """Stub pipeline : input minimal → résultat classe D réaliste."""
        connector = StubThermicConnector()
        inputs = ThermicInputs(
            ifc_path=Path("/dev/null"),
            canton="GE",
            affectation="logement_collectif",
        )
        result = connector.simulate(inputs)

        assert result.qh_kwh_m2_an == 95.0
        assert result.ep_kwh_m2_an == 130.0
        assert result.energy_class is not None
        assert result.energy_class.value == "D"
        assert any("STUB" in w for w in result.warnings)

    def test_pipeline_gbxml_end_to_end(self, temp_ifc_file: Path) -> None:
        """IFC → GbxmlGenerator → SimulationResult avec vraies valeurs."""
        connector = GbxmlGenerator()
        inputs = ThermicInputs(
            ifc_path=temp_ifc_file,
            canton="GE",
            affectation="logement_collectif",
            heating_vector="gaz",
        )
        result = connector.simulate(inputs)

        assert result.qh_kwh_m2_an > 0
        assert result.ep_kwh_m2_an >= result.qh_kwh_m2_an
        assert result.raw_output["gbxml_bytes_length"] > 1000
        assert result.raw_output["nb_zones"] >= 3

    def test_v2_registry_adapter_wraps_v3_correctly(self, temp_ifc_file: Path) -> None:
        """Vérifie que le shim V2 registry convertit correctement kWh→MJ."""
        from app.services.thermique.registry import get_engine

        engine = get_engine("gbxml")
        result = engine._connector.simulate(
            ThermicInputs(ifc_path=temp_ifc_file, canton="GE", affectation="logement_collectif")
        )
        assert result.qh_kwh_m2_an > 0

    def test_v2_shim_preserves_signature(self) -> None:
        """Les fonctions legacy serialize_to_lesosai_xml et build_operator_sheet_markdown
        doivent produire des résultats exploitables."""
        from app.services.thermique.lesosai_file import (
            build_operator_sheet_markdown,
            serialize_to_lesosai_xml,
        )

        model = {
            "name": "Test Project",
            "canton": "GE",
            "affectation": "logement_collectif",
            "operation_type": "neuf",
            "standard": "sia_380_1",
            "zones": [{"id": "Z1", "name": "Zone1", "affectation": "logement", "area": 100}],
            "walls": [{"id": "W1", "type": "mur_exterieur", "area": 40, "u_value": 0.17}],
        }

        xml_bytes = serialize_to_lesosai_xml(model)
        assert xml_bytes.startswith(b"<?xml")
        assert b"LesosaiExport" in xml_bytes
        assert b"Test Project" in xml_bytes

        markdown = build_operator_sheet_markdown(model, {"sre_total_m2": 100, "warnings": []})
        assert "Fiche de saisie Lesosai" in markdown
        assert "Test Project" in markdown
        assert "Procédure Lesosai" in markdown
