"""Agent métrés automatiques depuis un fichier IFC.

Extrait les quantités SIA 416 (surfaces brutes, nettes, SRE, volumes par CFC) et
produit un DPGF pré-rempli + un tableau de surfaces.

Gain : 1-2 jours d'ingénieur par affaire sur les phases 31-33.
"""
from __future__ import annotations

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from app.database import get_storage, get_supabase_admin
from app.services.excel_generator import generate_dpgf_xlsx
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


# Mapping IFC → catégorie CFC (eCCC-Bât simplifié)
IFC_TO_CFC: dict[str, str] = {
    "IfcWall": "214",           # 214 Murs porteurs / maçonnerie
    "IfcWallStandardCase": "214",
    "IfcSlab": "213",           # 213 Dalles
    "IfcBeam": "214",
    "IfcColumn": "214",
    "IfcFooting": "211",        # 211 Fouilles / fondations
    "IfcPile": "211",
    "IfcRoof": "224",           # 224 Couverture
    "IfcWindow": "221",         # 221 Fenêtres
    "IfcDoor": "222",           # 222 Portes
    "IfcStair": "215",          # 215 Escaliers
    "IfcRailing": "262",
    "IfcCovering": "281",       # 281 Revêtements
    "IfcFurniture": "411",      # 411 Mobilier
}


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Extrait les métrés SIA 416 d'un IFC et produit DPGF + tableau surfaces.

    Input params :
      - ifc_document_id: str (document IFC déjà uploadé)
      OU
      - ifc_storage_path: str (chemin direct)
    """
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    storage = get_storage()
    admin = get_supabase_admin()

    # Récupération de l'IFC
    ifc_bytes: bytes
    doc_id = params.get("ifc_document_id")
    if doc_id:
        doc = admin.table("documents").select("*").eq("id", doc_id).eq(
            "organization_id", org_id,
        ).maybe_single().execute()
        if not doc.data:
            raise ValueError("Document IFC introuvable")
        ifc_bytes = storage.download(doc.data["storage_path"])
        source_name = doc.data["filename"]
    else:
        path = params.get("ifc_storage_path")
        if not path:
            raise ValueError("ifc_document_id ou ifc_storage_path requis")
        ifc_bytes = storage.download(path)
        source_name = Path(path).name

    # Parsing IFC
    metres = _extract_metres(ifc_bytes)

    # Tableau surfaces SIA 416 (markdown)
    surfaces_md = _build_surfaces_table(metres)

    # DPGF Excel pré-rempli (structure par CFC)
    dpgf_items = _build_dpgf_items(metres)
    xlsx_bytes = generate_dpgf_xlsx(
        project_name=params.get("project_name", "Projet"),
        items=dpgf_items,
    )

    # PDF récapitulatif métrés
    full_md = f"""# Métrés automatiques SIA 416

**Projet** : {params.get('project_name', '')}
**Source IFC** : {source_name}
**Date extraction** : {datetime.now().strftime('%d.%m.%Y %H:%M')}

## Résumé

| Grandeur | Valeur |
|----------|--------|
| Nombre d'étages | {metres['nb_storeys']} |
| Nombre d'espaces (IfcSpace) | {metres['nb_spaces']} |
| Surface brute de plancher (SB) | {metres['sb_m2']} m² |
| Surface utile (SU) | {metres['su_m2']} m² |
| Surface de référence énergétique (SRE) | {metres['sre_m2']} m² |
| Volume bâti SIA 416 | {metres['volume_m3']} m³ |
| Surface enveloppe extérieure | {metres['envelope_m2']} m² |

## Détail par étage

{_render_storey_table(metres.get('by_storey', []))}

## Tableau surfaces SIA 416

{surfaces_md}

## Quantités par CFC (utilisées pour le DPGF)

{_render_cfc_table(metres.get('by_cfc', {}))}

## Remarques

- Les surfaces SU/SRE sont estimées à partir des IfcSpace quand Pset_SpaceCommon le permet.
  Sinon, approximation : SRE ≈ SB × 0.95, SU ≈ SB × 0.85 (à valider manuellement).
- Les quantités CFC sont issues du mapping IFC → eCCC-Bât simplifié. À confirmer avec le chiffreur.
- L'architecte et le chiffreur signataires engagent leur responsabilité sur les métrés officiels.
"""

    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(full_md),
        title="Métrés automatiques — SIA 416",
        project_name=params.get("project_name", ""),
        author=params.get("author", ""),
        reference=f"METRES-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = f"{org_id}/metres/{task['id']}"

    pdf_filename = f"metres_{ts}.pdf"
    pdf_path = f"{base_path}/{pdf_filename}"
    storage.upload(pdf_path, pdf_bytes, content_type="application/pdf")
    pdf_url = storage.get_signed_url(pdf_path, expires_in=604800)

    xlsx_filename = f"DPGF_pre_rempli_{ts}.xlsx"
    xlsx_path = f"{base_path}/{xlsx_filename}"
    storage.upload(xlsx_path, xlsx_bytes,
                   content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    admin.table("documents").insert([
        {
            "organization_id": org_id,
            "project_id": project_id,
            "filename": pdf_filename,
            "file_type": "pdf",
            "storage_path": pdf_path,
            "processed": True,
        },
        {
            "organization_id": org_id,
            "project_id": project_id,
            "filename": xlsx_filename,
            "file_type": "xlsx",
            "storage_path": xlsx_path,
            "processed": True,
        },
    ]).execute()

    return {
        "result_url": pdf_url,
        "preview": f"Métrés extraits : {metres['sb_m2']} m² SB, {metres['sre_m2']} m² SRE, {metres['volume_m3']} m³",
        "model": None,
        "tokens_used": 0,
        "cost_eur": 0,
        "email_bytes": pdf_bytes,
        "email_filename": pdf_filename,
        "metres": {
            "sb_m2": metres["sb_m2"],
            "sre_m2": metres["sre_m2"],
            "su_m2": metres["su_m2"],
            "volume_m3": metres["volume_m3"],
            "nb_spaces": metres["nb_spaces"],
        },
    }


def _extract_metres(ifc_bytes: bytes) -> dict[str, Any]:
    """Parse IFC et extrait toutes les quantités utiles."""
    import ifcopenshell
    import ifcopenshell.util.element as util_el

    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        tmp.write(ifc_bytes)
        tmp_path = tmp.name

    try:
        model = ifcopenshell.open(tmp_path)
    except Exception as exc:
        Path(tmp_path).unlink(missing_ok=True)
        raise ValueError(f"IFC illisible : {exc}")

    try:
        # Étages
        storeys = model.by_type("IfcBuildingStorey")
        by_storey: list[dict[str, Any]] = []
        total_sb = 0.0
        total_su = 0.0
        total_volume = 0.0
        nb_spaces_total = 0

        for storey in storeys:
            name = storey.Name or f"Étage_{storey.id()}"
            elevation = getattr(storey, "Elevation", None)

            sb_st = 0.0
            su_st = 0.0
            vol_st = 0.0
            nb_sp = 0

            # Parcours des IfcSpace directement rattachés
            for rel in getattr(storey, "ContainsElements", None) or []:
                for e in rel.RelatedElements:
                    if not e.is_a("IfcSpace"):
                        continue
                    nb_sp += 1
                    qtos = util_el.get_psets(e) or {}
                    bq = qtos.get("Qto_SpaceBaseQuantities") or qtos.get("BaseQuantities") or {}
                    gfa = _safe_num(bq.get("GrossFloorArea"))
                    nfa = _safe_num(bq.get("NetFloorArea"))
                    nv = _safe_num(bq.get("NetVolume")) or _safe_num(bq.get("GrossVolume"))
                    sb_st += gfa if gfa else (nfa * 1.1 if nfa else 0)
                    su_st += nfa if nfa else (gfa * 0.9 if gfa else 0)
                    vol_st += nv

            total_sb += sb_st
            total_su += su_st
            total_volume += vol_st
            nb_spaces_total += nb_sp

            by_storey.append({
                "name": name,
                "elevation_m": round(elevation, 2) if elevation is not None else None,
                "sb_m2": round(sb_st, 1),
                "su_m2": round(su_st, 1),
                "volume_m3": round(vol_st, 1),
                "nb_spaces": nb_sp,
            })

        # Fallback global si parcours par étage n'a rien donné
        if total_sb == 0:
            for sp in model.by_type("IfcSpace"):
                nb_spaces_total += 1
                qtos = util_el.get_psets(sp) or {}
                bq = qtos.get("Qto_SpaceBaseQuantities") or qtos.get("BaseQuantities") or {}
                gfa = _safe_num(bq.get("GrossFloorArea"))
                nfa = _safe_num(bq.get("NetFloorArea"))
                nv = _safe_num(bq.get("NetVolume")) or _safe_num(bq.get("GrossVolume"))
                total_sb += gfa if gfa else (nfa * 1.1 if nfa else 0)
                total_su += nfa if nfa else (gfa * 0.9 if gfa else 0)
                total_volume += nv

        # Enveloppe extérieure
        envelope_area = 0.0
        for wall_class in ("IfcWall", "IfcWallStandardCase"):
            try:
                for w in model.by_type(wall_class):
                    psets = util_el.get_psets(w) or {}
                    is_external = psets.get("Pset_WallCommon", {}).get("IsExternal")
                    if is_external is False:
                        continue
                    bq = psets.get("Qto_WallBaseQuantities") or {}
                    area = _safe_num(bq.get("NetSideArea")) or _safe_num(bq.get("GrossSideArea"))
                    envelope_area += area
            except Exception:
                continue

        for roof_class in ("IfcRoof", "IfcSlab"):
            try:
                for r in model.by_type(roof_class):
                    psets = util_el.get_psets(r) or {}
                    is_external = (
                        psets.get("Pset_RoofCommon", {}).get("IsExternal")
                        or psets.get("Pset_SlabCommon", {}).get("IsExternal")
                    )
                    if is_external is False:
                        continue
                    bq = psets.get("Qto_RoofBaseQuantities") or psets.get("Qto_SlabBaseQuantities") or {}
                    area = _safe_num(bq.get("NetArea")) or _safe_num(bq.get("GrossArea"))
                    envelope_area += area
            except Exception:
                continue

        # Quantités par CFC
        by_cfc: dict[str, dict[str, Any]] = {}
        for ifc_class, cfc in IFC_TO_CFC.items():
            try:
                elems = model.by_type(ifc_class)
            except Exception:
                continue
            if not elems:
                continue

            surface = 0.0
            volume = 0.0
            count = 0
            for e in elems:
                count += 1
                psets = util_el.get_psets(e) or {}
                for pset_name, pset_data in psets.items():
                    if not isinstance(pset_data, dict):
                        continue
                    if pset_name.startswith("Qto_"):
                        s = _safe_num(pset_data.get("NetArea")) or _safe_num(pset_data.get("GrossArea"))
                        v = _safe_num(pset_data.get("NetVolume")) or _safe_num(pset_data.get("GrossVolume"))
                        surface += s
                        volume += v

            key = cfc
            if key not in by_cfc:
                by_cfc[key] = {"surface_m2": 0.0, "volume_m3": 0.0, "count": 0, "ifc_classes": []}
            by_cfc[key]["surface_m2"] += surface
            by_cfc[key]["volume_m3"] += volume
            by_cfc[key]["count"] += count
            if ifc_class not in by_cfc[key]["ifc_classes"]:
                by_cfc[key]["ifc_classes"].append(ifc_class)

        for k in by_cfc:
            by_cfc[k]["surface_m2"] = round(by_cfc[k]["surface_m2"], 1)
            by_cfc[k]["volume_m3"] = round(by_cfc[k]["volume_m3"], 2)

        # Estimations SIA 380/1 SRE à partir de la SB si pas d'info directe
        sre_m2 = round(total_sb * 0.95, 1) if total_sb else 0

        return {
            "nb_storeys": len(storeys),
            "nb_spaces": nb_spaces_total,
            "sb_m2": round(total_sb, 1),
            "su_m2": round(total_su, 1),
            "sre_m2": sre_m2,
            "volume_m3": round(total_volume, 1),
            "envelope_m2": round(envelope_area, 1),
            "by_storey": by_storey,
            "by_cfc": by_cfc,
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _safe_num(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _build_surfaces_table(metres: dict[str, Any]) -> str:
    lines = [
        "| Code | Grandeur | Unité | Valeur |",
        "|------|----------|-------|--------|",
        f"| SB | Surface brute de plancher | m² | {metres['sb_m2']} |",
        f"| SU | Surface utile (estimée) | m² | {metres['su_m2']} |",
        f"| SRE | Surface de référence énergétique (≈ 0.95 × SB) | m² | {metres['sre_m2']} |",
        f"| V | Volume bâti SIA 416 | m³ | {metres['volume_m3']} |",
        f"| A_env | Surface enveloppe extérieure | m² | {metres['envelope_m2']} |",
    ]
    return "\n".join(lines)


def _render_storey_table(storeys: list[dict[str, Any]]) -> str:
    if not storeys:
        return "_Aucune donnée par étage disponible (IFC sans IfcBuildingStorey hiérarchique)._"
    lines = ["| Étage | Altitude | SB (m²) | SU (m²) | Volume (m³) | Nb espaces |",
             "|-------|----------|---------|---------|-------------|------------|"]
    for s in storeys:
        el = f"{s['elevation_m']} m" if s.get("elevation_m") is not None else "—"
        lines.append(
            f"| {s['name']} | {el} | {s['sb_m2']} | {s['su_m2']} | {s['volume_m3']} | {s['nb_spaces']} |"
        )
    return "\n".join(lines)


def _render_cfc_table(by_cfc: dict[str, dict[str, Any]]) -> str:
    if not by_cfc:
        return "_Aucune donnée CFC extraite._"
    lines = ["| CFC | Surface (m²) | Volume (m³) | Nb éléments | Classes IFC |",
             "|-----|--------------|-------------|-------------|-------------|"]
    for cfc in sorted(by_cfc.keys()):
        data = by_cfc[cfc]
        lines.append(
            f"| {cfc} | {data['surface_m2']} | {data['volume_m3']} | "
            f"{data['count']} | {', '.join(data['ifc_classes'])} |"
        )
    return "\n".join(lines)


def _build_dpgf_items(metres: dict[str, Any]) -> list[dict[str, Any]]:
    """Transforme les quantités en lignes DPGF par CFC."""
    cfc_labels = {
        "211": "Fouilles et fondations",
        "213": "Dalles",
        "214": "Murs porteurs, poteaux, poutres",
        "215": "Escaliers",
        "221": "Fenêtres",
        "222": "Portes extérieures",
        "224": "Couverture / toiture",
        "262": "Gardes-corps, balustrades",
        "281": "Revêtements intérieurs",
        "411": "Mobilier fixe",
    }
    items = []
    for cfc, data in sorted(metres.get("by_cfc", {}).items()):
        label = cfc_labels.get(cfc, f"CFC {cfc}")
        quantity = data["surface_m2"] if data["surface_m2"] > 0 else data["count"]
        unit = "m²" if data["surface_m2"] > 0 else "u"
        items.append({
            "lot": f"{cfc} {label}",
            "designation": f"{label} (métré automatique depuis IFC)",
            "unit": unit,
            "quantity": quantity,
            "unit_price_eur": 0,  # À remplir par le chiffreur
            "total_eur": 0,
            "notes": f"Classes IFC sources : {', '.join(data['ifc_classes'])}",
        })
    return items
