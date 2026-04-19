"""Tests unitaires pour CecbParser."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.connectors.thermic import ConnectorError, EnergyClass, ThermicInputs
from app.connectors.thermic.cecb_parser import CecbParser


class TestCecbParser:
    def test_parse_sample_file_extracts_qh(self, temp_cecb_file: Path) -> None:
        parser = CecbParser()
        inputs = ThermicInputs(
            ifc_path=temp_cecb_file, canton="GE", affectation="logement_collectif",
        )
        result = parser.simulate(inputs)

        assert result.qh_kwh_m2_an == 75.3, "Qh du sample XML = 75.3 kWh/m²·an"
        assert result.sre_m2 == 1250.0
        assert result.energy_class == EnergyClass.C

    def test_parse_extracts_idc(self, temp_cecb_file: Path) -> None:
        parser = CecbParser()
        inputs = ThermicInputs(
            ifc_path=temp_cecb_file, canton="GE", affectation="logement_collectif",
        )
        result = parser.simulate(inputs)
        assert result.idc_kwh_m2_an == 97.4

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        parser = CecbParser()
        missing = tmp_path / "nope.xml"
        inputs = ThermicInputs(ifc_path=missing, canton="GE")
        with pytest.raises(ConnectorError, match="introuvable"):
            parser.simulate(inputs)

    def test_malformed_xml_raises(self, tmp_path: Path) -> None:
        parser = CecbParser()
        bad = tmp_path / "bad.xml"
        bad.write_text("<not_xml<<<")
        inputs = ThermicInputs(ifc_path=bad, canton="GE")
        with pytest.raises(ConnectorError, match="malformé"):
            parser.simulate(inputs)

    def test_compliant_flag_matches_limite(self, temp_cecb_file: Path) -> None:
        parser = CecbParser()
        inputs = ThermicInputs(
            ifc_path=temp_cecb_file, canton="GE", affectation="logement_collectif",
        )
        result = parser.simulate(inputs)

        # Limite SIA 380/1 logement collectif = 44.0 kWh/m²·an
        # Qh dans sample = 75.3 → non conforme
        assert result.qh_limite_kwh_m2_an == 44.0
        assert result.compliant is False, \
            "75.3 > 44.0 donc non conforme à la limite SIA 380/1"

    def test_mj_auto_conversion_to_kwh(self, tmp_path: Path) -> None:
        """Si l'IDC XML est en MJ (>1000), conversion auto en kWh."""
        xml_with_mj = """<?xml version="1.0"?>
<CECB>
    <Qh unit="kWh/m2a">60</Qh>
    <SRE>1000</SRE>
    <IDC unit="MJ/m2a">2500</IDC>
    <ClasseGlobale>C</ClasseGlobale>
</CECB>"""
        path = tmp_path / "cecb_mj.xml"
        path.write_text(xml_with_mj)

        parser = CecbParser()
        inputs = ThermicInputs(ifc_path=path, canton="GE", affectation="logement_collectif")
        result = parser.simulate(inputs)

        # 2500 MJ / 3.6 = 694.44 kWh
        assert abs(result.idc_kwh_m2_an - 694.44) < 0.5, \
            f"IDC 2500 MJ doit être converti à ~694 kWh, obtenu {result.idc_kwh_m2_an}"
        assert any("MJ" in w for w in result.warnings)
