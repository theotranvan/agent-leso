"""Tests du sérialiseur XML Lesosai et de la fiche opérateur."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from app.services.thermique.lesosai_file import (
    build_operator_sheet_markdown,
    serialize_to_lesosai_xml,
)

FULL_MODEL = {
    "name": "Les Tilleuls",
    "canton": "GE",
    "affectation": "logement_collectif",
    "operation_type": "neuf",
    "standard": "sia_380_1",
    "zones": [
        {
            "id": "z1",
            "name": "Bâtiment",
            "affectation": "logement_collectif",
            "area": 940,
            "volume": 2300,
            "temp_setpoint": 20,
        }
    ],
    "walls": [
        {"id": "w1", "type": "mur_exterieur", "area": 456, "u_value": 0.17},
        {"id": "w2", "type": "toiture", "area": 345, "u_value": 0.15},
    ],
    "openings": [
        {
            "id": "o1",
            "type": "fenetre",
            "area": 30,
            "u_value": 1.0,
            "g_value": 0.5,
            "orientation": "S",
        }
    ],
    "thermal_bridges": [],
    "systems": {},
}


class TestSerializeToLesosaiXml:
    def _parse(self, model: dict) -> ET.Element:
        return ET.fromstring(serialize_to_lesosai_xml(model))

    def test_zones_non_vides_sont_incluses(self) -> None:
        root = self._parse(FULL_MODEL)
        zones = root.find("Zones")
        assert zones is not None
        assert len(list(zones)) == 1
        zone = zones[0]
        assert zone.findtext("Name") == "Bâtiment"
        assert zone.findtext("AreaM2") == "940"
        assert zone.findtext("VolumeM3") == "2300"

    def test_parois_incluses(self) -> None:
        root = self._parse(FULL_MODEL)
        walls = root.find("Walls")
        assert walls is not None
        assert len(list(walls)) == 2

    def test_ouvertures_incluses(self) -> None:
        root = self._parse(FULL_MODEL)
        openings = root.find("Openings")
        assert openings is not None
        assert len(list(openings)) == 1
        op = openings[0]
        assert op.findtext("UValueWm2K") == "1.0"
        assert op.findtext("GValue") == "0.5"

    def test_zones_vides_quand_modele_sans_zones(self) -> None:
        model = {**FULL_MODEL, "zones": []}
        root = self._parse(model)
        zones = root.find("Zones")
        assert zones is not None
        assert len(list(zones)) == 0

    def test_encodage_utf8_valide(self) -> None:
        xml_bytes = serialize_to_lesosai_xml(FULL_MODEL)
        assert xml_bytes.startswith(b"<?xml")
        # Doit se décoder proprement en UTF-8 sans UnicodeDecodeError.
        decoded = xml_bytes.decode("utf-8")
        assert "Bâtiment" in decoded
        assert "intermédiaire" in decoded

    def test_projet_metadata(self) -> None:
        root = self._parse(FULL_MODEL)
        project = root.find("Project")
        assert project is not None
        assert project.findtext("Name") == "Les Tilleuls"
        assert project.findtext("Canton") == "GE"


class TestBuildOperatorSheet:
    def test_contient_sections_zones_parois_ouvertures(self) -> None:
        sheet = build_operator_sheet_markdown(FULL_MODEL, {"sre_total_m2": 940, "warnings": []})
        assert "Bâtiment" in sheet
        assert "mur_exterieur" in sheet
        assert "fenetre" in sheet

    def test_warnings_apparaissent(self) -> None:
        sheet = build_operator_sheet_markdown(
            FULL_MODEL,
            {"sre_total_m2": 940, "warnings": ["Attention test"]},
        )
        assert "Attention test" in sheet
