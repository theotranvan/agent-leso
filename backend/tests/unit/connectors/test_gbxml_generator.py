"""Tests unitaires pour GbxmlGenerator."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from app.connectors.thermic import ConnectorError, SimulationResult, ThermicInputs
from app.connectors.thermic.gbxml_generator import GBXML_NAMESPACE, GbxmlGenerator


class TestGbxmlGenerator:
    def test_validate_inputs_missing_file_raises(self, tmp_path: Path) -> None:
        gen = GbxmlGenerator()
        missing = tmp_path / "nonexistent.ifc"
        inputs = ThermicInputs(ifc_path=missing, canton="GE")
        with pytest.raises(ConnectorError, match="IFC introuvable"):
            gen.validate_inputs(inputs)

    def test_simulate_produces_valid_result(self, temp_ifc_file: Path) -> None:
        gen = GbxmlGenerator()
        inputs = ThermicInputs(
            ifc_path=temp_ifc_file,
            canton="GE",
            affectation="logement_collectif",
            operation_type="neuf",
        )
        result = gen.simulate(inputs)

        assert isinstance(result, SimulationResult)
        assert result.engine_used == "gbxml_generator"
        assert result.qh_kwh_m2_an > 0, "Qh doit être strictement positif"
        assert result.sre_m2 > 0, "SRE doit être extraite et > 0"
        assert result.ep_kwh_m2_an >= result.qh_kwh_m2_an, \
            "Énergie primaire doit être >= Qh (facteur primaire)"
        assert result.computation_seconds > 0
        assert result.raw_output["nb_zones"] >= 3, "3 IfcSpace attendus"
        assert result.raw_output["nb_surfaces"] >= 6, "Au moins 4 murs + toit + dalle + fenêtre"

    def test_generated_gbxml_is_valid_xml(self, temp_ifc_file: Path) -> None:
        gen = GbxmlGenerator()
        inputs = ThermicInputs(ifc_path=temp_ifc_file, canton="GE", affectation="logement_collectif")
        xml_bytes = gen.generate_gbxml_bytes(inputs)

        assert xml_bytes.startswith(b"<?xml"), "Déclaration XML attendue en tête"
        root = ET.fromstring(xml_bytes)
        assert root.tag == f"{{{GBXML_NAMESPACE}}}gbXML"
        assert root.attrib.get("version") == "0.37"

        # Structure : Campus/Building/Space
        campus = root.find(f"{{{GBXML_NAMESPACE}}}Campus")
        assert campus is not None
        building = campus.find(f"{{{GBXML_NAMESPACE}}}Building")
        assert building is not None
        spaces = building.findall(f"{{{GBXML_NAMESPACE}}}Space")
        assert len(spaces) >= 3

    def test_qh_consistency_with_ua_hdd(self, temp_ifc_file: Path) -> None:
        """Vérifie Qh ≈ UA × HDD × 24 / 1000 / SRE."""
        gen = GbxmlGenerator()
        inputs = ThermicInputs(ifc_path=temp_ifc_file, canton="GE",
                               affectation="logement_collectif")
        result = gen.simulate(inputs)

        ua = result.raw_output["ua_total_wk"]
        sre = result.sre_m2
        hdd_geneva = 3050
        qh_expected = ua * hdd_geneva * 24 / 1000 / sre

        assert abs(result.qh_kwh_m2_an - qh_expected) < 0.1, \
            f"Qh {result.qh_kwh_m2_an} ne correspond pas à la formule UA·HDD ({qh_expected})"

    def test_compliance_check_against_sia_limit(self, temp_ifc_file: Path) -> None:
        gen = GbxmlGenerator()
        inputs = ThermicInputs(ifc_path=temp_ifc_file, canton="GE",
                               affectation="logement_collectif")
        result = gen.simulate(inputs)

        assert result.qh_limite_kwh_m2_an == 44.0, \
            "Limite SIA 380/1 pour logement collectif = 44 kWh/m²·an"
        expected_compliant = result.qh_kwh_m2_an <= 44.0
        assert result.compliant == expected_compliant

    def test_primary_factor_differs_by_vector(self, temp_ifc_file: Path) -> None:
        gen = GbxmlGenerator()
        base = {"ifc_path": temp_ifc_file, "canton": "GE", "affectation": "logement_collectif"}

        result_gas = gen.simulate(ThermicInputs(**base, heating_vector="gaz"))
        result_pac = gen.simulate(ThermicInputs(**base, heating_vector="pac_sol_eau"))
        result_elec = gen.simulate(ThermicInputs(**base, heating_vector="electrique"))

        # Même Qh (géométrie identique) mais Ep très différent
        assert abs(result_gas.qh_kwh_m2_an - result_pac.qh_kwh_m2_an) < 0.01
        assert result_elec.ep_kwh_m2_an > result_gas.ep_kwh_m2_an > result_pac.ep_kwh_m2_an, \
            f"Ordre attendu : PAC < gaz < élec, obtenu PAC={result_pac.ep_kwh_m2_an} " \
            f"gaz={result_gas.ep_kwh_m2_an} élec={result_elec.ep_kwh_m2_an}"
