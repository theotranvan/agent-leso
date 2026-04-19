"""Parser IFC/BCF via IfcOpenShell."""
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.util.element

logger = logging.getLogger(__name__)


def _open_ifc(ifc_bytes: bytes) -> ifcopenshell.file:
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        tmp.write(ifc_bytes)
        path = tmp.name
    model = ifcopenshell.open(path)
    Path(path).unlink(missing_ok=True)
    return model


def parse_ifc_metadata(ifc_bytes: bytes) -> dict[str, Any]:
    try:
        m = _open_ifc(ifc_bytes)
        project = m.by_type("IfcProject")[0] if m.by_type("IfcProject") else None
        building = m.by_type("IfcBuilding")[0] if m.by_type("IfcBuilding") else None
        return {
            "schema": m.schema,
            "project_name": project.Name if project else None,
            "building_name": building.Name if building else None,
            "nb_storeys": len(m.by_type("IfcBuildingStorey")),
            "nb_spaces": len(m.by_type("IfcSpace")),
            "nb_walls": len(m.by_type("IfcWall")),
            "nb_slabs": len(m.by_type("IfcSlab")),
            "nb_windows": len(m.by_type("IfcWindow")),
            "nb_doors": len(m.by_type("IfcDoor")),
            "nb_columns": len(m.by_type("IfcColumn")),
            "nb_beams": len(m.by_type("IfcBeam")),
        }
    except Exception as e:
        logger.error(f"parse_ifc_metadata: {e}")
        return {"error": str(e)}


def _extract_material_info(material) -> list[dict]:
    infos = []
    try:
        if material.is_a("IfcMaterial"):
            infos.append({"name": material.Name, "category": getattr(material, "Category", None)})
        elif material.is_a("IfcMaterialLayerSetUsage"):
            ls = material.ForLayerSet
            for layer in ls.MaterialLayers or []:
                infos.append({"name": layer.Material.Name if layer.Material else "?",
                              "thickness": layer.LayerThickness})
        elif material.is_a("IfcMaterialLayerSet"):
            for layer in material.MaterialLayers or []:
                infos.append({"name": layer.Material.Name if layer.Material else "?",
                              "thickness": layer.LayerThickness})
        elif material.is_a("IfcMaterialConstituentSet"):
            for c in material.MaterialConstituents or []:
                infos.append({"name": c.Material.Name if c.Material else "?",
                              "fraction": getattr(c, "Fraction", None)})
    except Exception as e:
        logger.warning(f"material: {e}")
    return infos


def extract_thermal_properties(ifc_bytes: bytes) -> list[dict]:
    """Props thermiques (U-values, matériaux) pour RE2020."""
    results = []
    try:
        m = _open_ifc(ifc_bytes)
        for t in ["IfcWall", "IfcSlab", "IfcRoof", "IfcWindow", "IfcDoor", "IfcCurtainWall"]:
            for el in m.by_type(t):
                psets = ifcopenshell.util.element.get_psets(el)
                thermal = {}
                for name, data in psets.items():
                    if "Thermal" in name:
                        thermal.update(data)
                mats = ifcopenshell.util.element.get_material(el, should_inherit=True)
                mat_info = _extract_material_info(mats) if mats else []
                if thermal or mat_info:
                    results.append({
                        "type": t, "name": el.Name or "", "global_id": el.GlobalId,
                        "thermal_properties": thermal, "materials": mat_info,
                    })
    except Exception as e:
        logger.error(f"thermal: {e}")
    return results


def extract_structural_elements(ifc_bytes: bytes) -> list[dict]:
    results = []
    try:
        m = _open_ifc(ifc_bytes)
        for t in ["IfcColumn", "IfcBeam", "IfcSlab", "IfcWall", "IfcFooting"]:
            for el in m.by_type(t):
                psets = ifcopenshell.util.element.get_psets(el)
                qtos = {k: v for k, v in psets.items() if k.startswith("Qto_")}
                results.append({
                    "type": t, "name": el.Name or "", "global_id": el.GlobalId,
                    "quantities": qtos, "object_type": getattr(el, "ObjectType", None),
                })
    except Exception as e:
        logger.error(f"structural: {e}")
    return results


def extract_spaces_and_surfaces(ifc_bytes: bytes) -> list[dict]:
    results = []
    try:
        m = _open_ifc(ifc_bytes)
        for space in m.by_type("IfcSpace"):
            psets = ifcopenshell.util.element.get_psets(space)
            qto = psets.get("Qto_SpaceBaseQuantities", {})
            results.append({
                "name": space.Name, "long_name": getattr(space, "LongName", None),
                "area": qto.get("NetFloorArea") or qto.get("GrossFloorArea"),
                "volume": qto.get("NetVolume") or qto.get("GrossVolume"),
                "height": qto.get("Height"),
            })
    except Exception as e:
        logger.error(f"spaces: {e}")
    return results


def _bbox_intersects(a: tuple, b: tuple, tol: float = 0.01) -> bool:
    return (a[0] - tol <= b[3] and a[3] + tol >= b[0] and
            a[1] - tol <= b[4] and a[4] + tol >= b[1] and
            a[2] - tol <= b[5] and a[5] + tol >= b[2])


def detect_clashes(ifc_models_bytes: list[tuple[str, bytes]]) -> list[dict]:
    """Détection de conflits inter-lots via bounding boxes IFC."""
    from ifcopenshell.geom import settings as gs, create_shape
    s = gs()
    s.set(s.USE_WORLD_COORDS, True)
    elements = []
    for lot, ifc_bytes in ifc_models_bytes:
        try:
            m = _open_ifc(ifc_bytes)
            for el in m.by_type("IfcProduct"):
                if not el.Representation:
                    continue
                try:
                    shape = create_shape(s, el)
                    verts = shape.geometry.verts
                    if not verts:
                        continue
                    xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
                    bbox = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))
                    elements.append({
                        "lot": lot, "global_id": el.GlobalId, "type": el.is_a(),
                        "name": el.Name or "", "bbox": bbox,
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"clash parse {lot}: {e}")

    clashes = []
    for i, a in enumerate(elements):
        for b in elements[i + 1:]:
            if a["lot"] == b["lot"]:
                continue
            if _bbox_intersects(a["bbox"], b["bbox"]):
                clashes.append({
                    "element_a": {"lot": a["lot"], "type": a["type"], "name": a["name"], "id": a["global_id"]},
                    "element_b": {"lot": b["lot"], "type": b["type"], "name": b["name"], "id": b["global_id"]},
                })
    return clashes


def generate_bcf_xml(clashes: list[dict], project_name: str = "Coordination") -> str:
    """Génère un BCF XML 2.1 depuis une liste de clashes."""
    topics = []
    for i, c in enumerate(clashes, 1):
        guid = str(uuid.uuid4())
        topics.append(f"""  <Topic Guid="{guid}" TopicType="Clash" TopicStatus="Open">
    <Title>Conflit {i}: {c['element_a']['lot']} × {c['element_b']['lot']}</Title>
    <CreationDate>{datetime.utcnow().isoformat()}Z</CreationDate>
    <CreationAuthor>BET Agent IA</CreationAuthor>
    <Description>Élément A: {c['element_a']['type']} "{c['element_a']['name']}" (lot {c['element_a']['lot']}) / Élément B: {c['element_b']['type']} "{c['element_b']['name']}" (lot {c['element_b']['lot']})</Description>
  </Topic>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Markup xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <Header><ProjectName>{project_name}</ProjectName><Version>2.1</Version></Header>
{chr(10).join(topics)}
</Markup>"""
