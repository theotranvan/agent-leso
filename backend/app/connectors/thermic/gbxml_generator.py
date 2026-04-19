"""Générateur gbXML v0.37 depuis un fichier IFC.

gbXML (Green Building XML) est un format d'échange ouvert pour les données thermiques
de bâtiment, supporté par EnergyPlus, IES-VE, Trace 700, et divers moteurs SIA 380/1.

Pipeline :
1. Lire l'IFC avec ifcopenshell
2. Extraire : Site, Building, Spaces (IfcSpace), Walls, Roofs, Slabs, Windows, Doors
3. Calculer U-values depuis Pset_*Common si présents, sinon fallback SIA 380/1
4. Construire l'arbre gbXML <gbXML xmlns="http://www.gbxml.org/schema"...>
5. Si GBXML_XSD_PATH défini en env, valider avec lxml.etree.XMLSchema
6. Sérialiser en bytes UTF-8

Le résultat peut être consommé par un moteur SIA 380/1 (Lesosai acceptant gbXML)
ou servir d'input à un CECB validator tiers.

Limitations V3 :
- Géométrie simplifiée en axis-aligned bounding boxes (orthogonal only)
- Pas de détection automatique de thermal zones fines (1 zone = 1 space IFC)
- Ombrage / masques externes non extraits
"""
from __future__ import annotations

import logging
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.connectors.thermic.base import (
    ConnectorError,
    SimulationResult,
    ThermicConnector,
    ThermicInputs,
    default_u_value,
    limite_qh_for_affectation,
    qh_to_energy_class,
)

logger = logging.getLogger(__name__)

GBXML_NAMESPACE = "http://www.gbxml.org/schema"
GBXML_VERSION = "0.37"


@dataclass
class GbxmlZone:
    """Zone thermique extraite d'un IfcSpace."""

    space_id: str
    name: str
    area_m2: float
    volume_m3: float
    height_m: float
    level_name: str


@dataclass
class GbxmlSurface:
    """Surface d'enveloppe (mur, toit, dalle, ouverture)."""

    surface_id: str
    surface_type: str  # ExteriorWall, InteriorWall, Roof, SlabOnGrade, etc.
    area_m2: float
    u_value: float
    adjacent_zone_id: str | None = None
    openings: list[GbxmlSurface] | None = None  # windows/doors


class GbxmlGenerator(ThermicConnector):
    """IFC → gbXML v0.37 + calcul Qh simplifié + détection classe énergétique."""

    name = "gbxml_generator"

    def __init__(self) -> None:
        self.xsd_path = os.environ.get("GBXML_XSD_PATH")
        self._xsd = None
        if self.xsd_path and Path(self.xsd_path).exists():
            try:
                from lxml import etree
                self._xsd = etree.XMLSchema(etree.parse(self.xsd_path))
                logger.info("gbXML XSD chargé depuis %s", self.xsd_path)
            except Exception as exc:
                logger.warning("Impossible de charger le XSD gbXML : %s", exc)

    def validate_inputs(self, inputs: ThermicInputs) -> list[str]:
        warnings: list[str] = []
        if not inputs.ifc_path.exists():
            raise ConnectorError(f"IFC introuvable : {inputs.ifc_path}")
        if inputs.ifc_path.suffix.lower() not in {".ifc", ".ifczip"}:
            raise ConnectorError(f"Extension non supportée : {inputs.ifc_path.suffix}")
        size_mb = inputs.ifc_path.stat().st_size / (1024 * 1024)
        if size_mb > 500:
            warnings.append(f"IFC volumineux ({size_mb:.1f} MB) - traitement pouvant être lent")
        if size_mb < 0.001:
            raise ConnectorError("IFC vide ou corrompu")
        return warnings

    def simulate(self, inputs: ThermicInputs) -> SimulationResult:
        start = time.monotonic()
        warnings = self.validate_inputs(inputs)

        try:
            import ifcopenshell
            import ifcopenshell.util.element
        except ImportError as exc:
            raise ConnectorError("ifcopenshell non installé") from exc

        try:
            ifc = ifcopenshell.open(str(inputs.ifc_path))
        except Exception as exc:
            raise ConnectorError(f"Lecture IFC échouée : {exc}") from exc

        zones = self._extract_zones(ifc, warnings)
        surfaces = self._extract_surfaces(ifc, warnings)

        if not zones:
            raise ConnectorError("Aucun IfcSpace exploitable dans l'IFC")

        total_area = inputs.sre_m2 or sum(z.area_m2 for z in zones)
        if total_area <= 0:
            raise ConnectorError("Surface totale nulle ou négative")

        # Calcul Qh simplifié : Somme(U·A) × HDD / SRE
        qh_kwh_m2_an = self._estimate_qh(surfaces, total_area, inputs.canton)

        # Énergie primaire : Qh + forfait ECS + facteur vecteur
        ecs_forfait = 20.0 if inputs.affectation.startswith("logement") else 7.0
        primary_factor = self._primary_factor(inputs.heating_vector)
        ep_kwh_m2_an = (qh_kwh_m2_an + ecs_forfait) * primary_factor

        qh_limite = limite_qh_for_affectation(inputs.affectation)
        compliant = qh_kwh_m2_an <= qh_limite if qh_limite else None

        # Génération du gbXML (sérialisation + validation optionnelle)
        xml_bytes = self._build_gbxml(zones, surfaces, inputs)
        validation_warnings = self._validate_xsd(xml_bytes)
        warnings.extend(validation_warnings)

        elapsed = time.monotonic() - start
        logger.info(
            "gbXML généré : %d zones, %d surfaces, %.2fs",
            len(zones), len(surfaces), elapsed,
        )

        return SimulationResult(
            qh_kwh_m2_an=qh_kwh_m2_an,
            ep_kwh_m2_an=ep_kwh_m2_an,
            sre_m2=total_area,
            idc_kwh_m2_an=qh_kwh_m2_an + ecs_forfait if inputs.canton == "GE" else None,
            qh_limite_kwh_m2_an=qh_limite,
            energy_class=qh_to_energy_class(qh_kwh_m2_an),
            compliant=compliant,
            engine_used=self.name,
            computation_seconds=elapsed,
            warnings=warnings,
            raw_output={
                "gbxml_bytes_length": len(xml_bytes),
                "nb_zones": len(zones),
                "nb_surfaces": len(surfaces),
                "ua_total_wk": self._ua_total(surfaces),
            },
        )

    def generate_gbxml_bytes(self, inputs: ThermicInputs) -> bytes:
        """Exposé séparé : génère uniquement le gbXML sans calcul.

        Utile pour pipeline externe (Lesosai qui accepte gbXML).
        """
        warnings = self.validate_inputs(inputs)
        if warnings:
            logger.info("gbXML warnings : %s", warnings)

        import ifcopenshell

        ifc = ifcopenshell.open(str(inputs.ifc_path))
        zones = self._extract_zones(ifc, [])
        surfaces = self._extract_surfaces(ifc, [])
        return self._build_gbxml(zones, surfaces, inputs)

    # ---------- helpers extraction ----------

    def _extract_zones(self, ifc: Any, warnings: list[str]) -> list[GbxmlZone]:
        zones: list[GbxmlZone] = []
        try:
            spaces = ifc.by_type("IfcSpace")
        except Exception as exc:
            logger.warning("Extraction IfcSpace échouée : %s", exc)
            return zones

        for space in spaces:
            qtos = self._extract_quantities(space)
            area = qtos.get("NetFloorArea") or qtos.get("GrossFloorArea") or 0.0
            volume = qtos.get("NetVolume") or qtos.get("GrossVolume") or 0.0
            height = qtos.get("Height") or (volume / area if area > 0 else 2.8)

            storey = self._get_storey_name(space)
            zones.append(GbxmlZone(
                space_id=space.GlobalId or f"space_{space.id()}",
                name=space.Name or f"Space_{space.id()}",
                area_m2=float(area),
                volume_m3=float(volume),
                height_m=float(height),
                level_name=storey,
            ))
        if not zones:
            warnings.append("Aucun IfcSpace trouvé - gbXML minimal sera généré")
        return zones

    def _extract_surfaces(self, ifc: Any, warnings: list[str]) -> list[GbxmlSurface]:
        surfaces: list[GbxmlSurface] = []

        # Murs
        try:
            for wall in ifc.by_type("IfcWall"):
                s = self._surface_from_element(wall, "ExteriorWall", "wall_external")
                if s:
                    surfaces.append(s)
        except Exception as exc:
            warnings.append(f"Extraction IfcWall échouée : {exc}")

        # Toits
        try:
            for roof in ifc.by_type("IfcRoof"):
                s = self._surface_from_element(roof, "Roof", "roof")
                if s:
                    surfaces.append(s)
        except Exception as exc:
            warnings.append(f"Extraction IfcRoof échouée : {exc}")

        # Dalles
        try:
            for slab in ifc.by_type("IfcSlab"):
                slab_type = self._slab_type(slab)
                elem_key = "slab_ground" if slab_type == "SlabOnGrade" else "wall_external"
                s = self._surface_from_element(slab, slab_type, elem_key)
                if s:
                    surfaces.append(s)
        except Exception as exc:
            warnings.append(f"Extraction IfcSlab échouée : {exc}")

        # Fenêtres (en tant que surfaces indépendantes pour simplification)
        try:
            for win in ifc.by_type("IfcWindow"):
                s = self._surface_from_element(win, "FixedWindow", "window")
                if s:
                    surfaces.append(s)
        except Exception as exc:
            warnings.append(f"Extraction IfcWindow échouée : {exc}")

        # Portes
        try:
            for door in ifc.by_type("IfcDoor"):
                s = self._surface_from_element(door, "NonSlidingDoor", "door")
                if s:
                    surfaces.append(s)
        except Exception as exc:
            warnings.append(f"Extraction IfcDoor échouée : {exc}")

        return surfaces

    def _surface_from_element(
        self,
        element: Any,
        gbxml_surface_type: str,
        default_u_key: str,
    ) -> GbxmlSurface | None:
        gid = getattr(element, "GlobalId", None) or f"{element.is_a()}_{element.id()}"
        area = self._extract_quantities(element).get("NetArea") \
            or self._extract_quantities(element).get("GrossArea") \
            or 0.0
        if area <= 0:
            return None

        u_value = self._extract_u_value(element) or default_u_value(default_u_key)

        return GbxmlSurface(
            surface_id=gid,
            surface_type=gbxml_surface_type,
            area_m2=float(area),
            u_value=float(u_value),
        )

    @staticmethod
    def _extract_quantities(element: Any) -> dict[str, float]:
        import ifcopenshell.util.element as util

        try:
            psets = util.get_psets(element)
        except Exception:
            return {}
        qto: dict[str, float] = {}
        for pset_name, pset_data in (psets or {}).items():
            if not isinstance(pset_data, dict):
                continue
            for key, val in pset_data.items():
                if isinstance(val, (int, float)):
                    qto[key] = float(val)
        return qto

    @staticmethod
    def _extract_u_value(element: Any) -> float | None:
        import ifcopenshell.util.element as util

        try:
            psets = util.get_psets(element)
        except Exception:
            return None
        for pset_name in ("Pset_WallCommon", "Pset_RoofCommon", "Pset_SlabCommon",
                          "Pset_WindowCommon", "Pset_DoorCommon"):
            pset = (psets or {}).get(pset_name)
            if isinstance(pset, dict):
                u = pset.get("ThermalTransmittance")
                if isinstance(u, (int, float)) and u > 0:
                    return float(u)
        return None

    @staticmethod
    def _slab_type(slab: Any) -> str:
        predefined = getattr(slab, "PredefinedType", None) or ""
        mapping = {
            "FLOOR": "InteriorFloor",
            "ROOF": "Roof",
            "LANDING": "InteriorFloor",
            "BASESLAB": "SlabOnGrade",
        }
        return mapping.get(predefined.upper(), "InteriorFloor")

    @staticmethod
    def _get_storey_name(space: Any) -> str:
        try:
            for rel in space.Decomposes or []:
                parent = getattr(rel, "RelatingObject", None)
                if parent and parent.is_a("IfcBuildingStorey"):
                    return parent.Name or "Unknown"
        except Exception:
            pass
        return "Unknown"

    # ---------- calcul thermique simplifié ----------

    def _estimate_qh(self, surfaces: list[GbxmlSurface], sre_m2: float, canton: str) -> float:
        """Qh ≈ Σ(U·A)·HDD·24 / SRE / 1000 en kWh/m²·an."""
        hdd = {"GE": 3050, "VD": 3150, "NE": 3280, "FR": 3550, "VS": 3100, "JU": 3300}.get(canton, 3200)
        ua_total = self._ua_total(surfaces)
        if sre_m2 <= 0:
            return 0.0
        # Facteur 0.024 = 24h × 365j / 1000 / 365  (conversion kWh)
        losses_kwh = ua_total * hdd * 24 / 1000
        return losses_kwh / sre_m2

    @staticmethod
    def _ua_total(surfaces: list[GbxmlSurface]) -> float:
        # Seules les surfaces vers l'extérieur contribuent aux pertes
        exterior_types = {"ExteriorWall", "Roof", "SlabOnGrade", "FixedWindow", "NonSlidingDoor"}
        return sum(s.u_value * s.area_m2 for s in surfaces if s.surface_type in exterior_types)

    @staticmethod
    def _primary_factor(vector: str) -> float:
        # Facteurs indicatifs énergie finale → primaire (SIA 380/1 annexe)
        mapping = {
            "gaz": 1.05, "mazout": 1.10, "chauffage_distance": 0.70,
            "pac_air_eau": 0.80, "pac_sol_eau": 0.65,
            "pellet": 0.30, "buche": 0.20, "electrique": 2.00,
            "solaire_thermique": 0.10,
        }
        return mapping.get(vector, 1.0)

    # ---------- construction gbXML ----------

    def _build_gbxml(
        self,
        zones: list[GbxmlZone],
        surfaces: list[GbxmlSurface],
        inputs: ThermicInputs,
    ) -> bytes:
        # Registration du namespace pour sortie propre
        ET.register_namespace("", GBXML_NAMESPACE)

        root = ET.Element(
            f"{{{GBXML_NAMESPACE}}}gbXML",
            attrib={
                "version": GBXML_VERSION,
                "temperatureUnit": "C",
                "lengthUnit": "Meters",
                "areaUnit": "SquareMeters",
                "volumeUnit": "CubicMeters",
                "useSIUnitsForResults": "true",
            },
        )

        # Campus / Location
        campus = ET.SubElement(root, f"{{{GBXML_NAMESPACE}}}Campus", id="campus-1")
        location = ET.SubElement(campus, f"{{{GBXML_NAMESPACE}}}Location")
        self._sub_text(location, "Name", inputs.canton or "CH")
        self._sub_text(location, "ZipcodeOrPostalCode", "")
        self._sub_text(location, "Latitude", self._canton_latitude(inputs.canton))
        self._sub_text(location, "Longitude", self._canton_longitude(inputs.canton))

        # Building
        building = ET.SubElement(
            campus, f"{{{GBXML_NAMESPACE}}}Building",
            id="bldg-1", buildingType=self._gbxml_building_type(inputs.affectation),
        )
        self._sub_text(building, "Name", "Building")
        self._sub_text(building, "Area", str(sum(z.area_m2 for z in zones)))

        # Spaces
        for zone in zones:
            sp = ET.SubElement(
                building, f"{{{GBXML_NAMESPACE}}}Space",
                id=self._safe_id(zone.space_id),
                zoneIdRef=f"zone-{self._safe_id(zone.space_id)}",
            )
            self._sub_text(sp, "Name", zone.name)
            self._sub_text(sp, "Area", str(round(zone.area_m2, 3)))
            self._sub_text(sp, "Volume", str(round(zone.volume_m3, 3)))

        # Surfaces (au niveau Campus dans gbXML standard)
        for surf in surfaces:
            s_el = ET.SubElement(
                campus, f"{{{GBXML_NAMESPACE}}}Surface",
                id=self._safe_id(surf.surface_id),
                surfaceType=surf.surface_type,
            )
            self._sub_text(s_el, "Name", surf.surface_id)
            rect = ET.SubElement(s_el, f"{{{GBXML_NAMESPACE}}}RectangularGeometry")
            self._sub_text(rect, "Azimuth", "0")
            self._sub_text(rect, "CartesianPoint", "0,0,0")
            self._sub_text(rect, "Tilt", "90" if "Wall" in surf.surface_type else "0")
            self._sub_text(rect, "Height", str(round(surf.area_m2 ** 0.5, 2)))
            self._sub_text(rect, "Width", str(round(surf.area_m2 ** 0.5, 2)))

        # Constructions - une par U-value distincte pour référence
        unique_u = sorted({round(s.u_value, 3) for s in surfaces})
        for idx, u in enumerate(unique_u, start=1):
            cons = ET.SubElement(
                root, f"{{{GBXML_NAMESPACE}}}Construction",
                id=f"cons-{idx}",
            )
            self._sub_text(cons, "U-value", str(u), unit="WPerSquareMeterK")
            self._sub_text(cons, "Name", f"Construction U={u}")

        # DocumentHistory
        doc = ET.SubElement(root, f"{{{GBXML_NAMESPACE}}}DocumentHistory")
        pr = ET.SubElement(doc, f"{{{GBXML_NAMESPACE}}}ProgramInfo", id="prog-betagent")
        self._sub_text(pr, "CompanyName", "BET Agent")
        self._sub_text(pr, "ProductName", "BET Agent V3")
        self._sub_text(pr, "Version", "3.0")

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")

        import io
        buf = io.BytesIO()
        tree.write(buf, encoding="utf-8", xml_declaration=True)
        return buf.getvalue()

    def _validate_xsd(self, xml_bytes: bytes) -> list[str]:
        """Valide avec le XSD gbXML si disponible, sinon validation structurelle légère."""
        warnings: list[str] = []
        if self._xsd is None:
            # Validation structurelle minimale (parse OK + éléments obligatoires)
            try:
                tree = ET.ElementTree(ET.fromstring(xml_bytes))
                root = tree.getroot()
                if not root.tag.endswith("gbXML"):
                    warnings.append("Racine gbXML manquante")
            except ET.ParseError as exc:
                warnings.append(f"gbXML malformé : {exc}")
            return warnings

        # Validation XSD complète
        try:
            from lxml import etree
            doc = etree.fromstring(xml_bytes)
            self._xsd.assertValid(doc)
        except Exception as exc:
            warnings.append(f"Validation XSD gbXML échouée : {exc}")
        return warnings

    @staticmethod
    def _sub_text(parent: ET.Element, tag: str, text: str, **attrs: str) -> ET.Element:
        el = ET.SubElement(parent, f"{{{GBXML_NAMESPACE}}}{tag}", attrib=attrs)
        el.text = text
        return el

    @staticmethod
    def _safe_id(raw: str) -> str:
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in raw[:64])

    @staticmethod
    def _gbxml_building_type(affectation: str) -> str:
        mapping = {
            "logement_individuel": "SingleFamily",
            "logement_collectif": "MultiFamily",
            "administration": "Office",
            "ecole": "School",
            "commerce": "Retail",
            "restauration": "Restaurant",
            "hopital": "Hospital",
            "industriel": "Warehouse",
            "depot": "Warehouse",
            "sport": "Recreation",
        }
        return mapping.get(affectation, "Unknown")

    @staticmethod
    def _canton_latitude(canton: str) -> str:
        return {"GE": "46.204", "VD": "46.520", "NE": "47.000",
                "FR": "46.806", "VS": "46.232", "JU": "47.365"}.get(canton, "46.8")

    @staticmethod
    def _canton_longitude(canton: str) -> str:
        return {"GE": "6.143", "VD": "6.633", "NE": "6.948",
                "FR": "7.161", "VS": "7.359", "JU": "7.344"}.get(canton, "7.0")
