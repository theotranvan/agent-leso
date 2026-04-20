"""Shim compat V2 pour les 3 fonctions utilisées par routes/thermique.py.

Ces fonctions existaient dans l'ancien `services/thermique/lesosai_file.py` V2.
Elles sont maintenant réimplémentées au-dessus des connectors V3 mais en gardant
exactement la même signature pour ne pas casser les routes.
"""
from __future__ import annotations

import io
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def serialize_to_lesosai_xml(thermal_model: dict) -> bytes:
    """Produit un XML interne structuré depuis un modèle thermique.

    Format interne BET Agent (pas Lesosai natif), lisible par un humain ou par le
    script RPA Lesosai de l'opérateur. Remplace l'ancienne fonction V2.
    """
    root = ET.Element("LesosaiExport", version="1.0", generator="BET-Agent-V3")
    meta = ET.SubElement(root, "Meta")
    ET.SubElement(meta, "ExportedAt").text = datetime.utcnow().isoformat()
    ET.SubElement(meta, "Notice").text = (
        "Fichier intermédiaire. Format interne BET Agent — à ouvrir en parallèle de Lesosai."
    )

    project = ET.SubElement(root, "Project")
    ET.SubElement(project, "Name").text = str(thermal_model.get("name", "Projet"))
    ET.SubElement(project, "Canton").text = str(thermal_model.get("canton", ""))
    ET.SubElement(project, "Affectation").text = str(thermal_model.get("affectation", ""))
    ET.SubElement(project, "OperationType").text = str(thermal_model.get("operation_type", ""))
    ET.SubElement(project, "Standard").text = str(thermal_model.get("standard", "sia_380_1"))

    # Climat
    climate = thermal_model.get("climate") or {}
    if climate:
        clim = ET.SubElement(project, "Climate")
        for k, v in climate.items():
            ET.SubElement(clim, str(k)).text = str(v)

    # Zones
    zones_el = ET.SubElement(root, "Zones")
    for z in thermal_model.get("zones") or []:
        zone = ET.SubElement(zones_el, "Zone", id=str(z.get("id", "")))
        ET.SubElement(zone, "Name").text = str(z.get("name", ""))
        ET.SubElement(zone, "Affectation").text = str(z.get("affectation", ""))
        ET.SubElement(zone, "AreaM2").text = str(z.get("area", 0))
        ET.SubElement(zone, "VolumeM3").text = str(z.get("volume", 0))
        ET.SubElement(zone, "TempSetpointC").text = str(z.get("temp_setpoint", 20))

    # Parois
    walls_el = ET.SubElement(root, "Walls")
    for w in thermal_model.get("walls") or []:
        wall = ET.SubElement(walls_el, "Wall", id=str(w.get("id", "")))
        ET.SubElement(wall, "Type").text = str(w.get("type", "mur_exterieur"))
        ET.SubElement(wall, "Orientation").text = str(w.get("orientation", ""))
        ET.SubElement(wall, "AreaM2").text = str(w.get("area", 0))
        ET.SubElement(wall, "UValueWm2K").text = str(w.get("u_value", ""))

    # Ouvertures
    openings_el = ET.SubElement(root, "Openings")
    for o in thermal_model.get("openings") or []:
        op = ET.SubElement(openings_el, "Opening", id=str(o.get("id", "")))
        ET.SubElement(op, "Type").text = str(o.get("type", "fenetre"))
        ET.SubElement(op, "AreaM2").text = str(o.get("area", 0))
        ET.SubElement(op, "UValueWm2K").text = str(o.get("u_value", ""))
        ET.SubElement(op, "GValue").text = str(o.get("g_value", ""))

    # Systèmes
    systems = thermal_model.get("systems") or {}
    if systems:
        sys_el = ET.SubElement(root, "Systems")
        for sname, sdata in systems.items():
            if isinstance(sdata, dict):
                s_sub = ET.SubElement(sys_el, str(sname).capitalize())
                for k, v in sdata.items():
                    ET.SubElement(s_sub, str(k)).text = str(v) if v is not None else ""

    buf = io.BytesIO()
    ET.ElementTree(root).write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue()


def build_operator_sheet_markdown(thermal_model: dict, prepared: dict) -> str:
    """Fiche opérateur à ouvrir en parallèle de Lesosai."""
    lines = ["# Fiche de saisie Lesosai", ""]
    lines.append(f"**Projet** : {thermal_model.get('name', '?')}")
    lines.append(f"**Canton** : {thermal_model.get('canton', '?')}")
    lines.append(f"**Affectation** : {thermal_model.get('affectation', '?')}")
    lines.append(f"**Opération** : {thermal_model.get('operation_type', '?')}")
    lines.append(f"**Standard visé** : {thermal_model.get('standard', 'sia_380_1')}")
    lines.append(f"**SRE totale** : {prepared.get('sre_total_m2', 0)} m²")
    lines.append("")

    if prepared.get("warnings"):
        lines.append("## ⚠ Points d'attention")
        for w in prepared["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    climate = thermal_model.get("climate") or {}
    if climate:
        lines.append("## 1. Station climatique")
        for k, v in climate.items():
            lines.append(f"- **{k}** : {v}")
        lines.append("")

    zones = thermal_model.get("zones") or []
    if zones:
        lines.append("## 2. Zones thermiques")
        lines.append("| Nom | Affectation | Surface m² | Volume m³ | T consigne |")
        lines.append("|---|---|---|---|---|")
        for z in zones:
            lines.append(
                f"| {z.get('name', '')} | {z.get('affectation', '')} | "
                f"{z.get('area', 0)} | {z.get('volume', 0)} | {z.get('temp_setpoint', 20)} |"
            )
        lines.append("")

    walls = thermal_model.get("walls") or []
    if walls:
        lines.append("## 3. Parois")
        lines.append("| Type | Orientation | Surface | U |")
        lines.append("|---|---|---|---|")
        for w in walls:
            lines.append(
                f"| {w.get('type', '')} | {w.get('orientation', '')} | "
                f"{w.get('area', 0)} m² | {w.get('u_value', '?')} W/m²K |"
            )
        lines.append("")

    openings = thermal_model.get("openings") or []
    if openings:
        lines.append("## 4. Ouvertures")
        lines.append("| Type | Orientation | Surface | U | g |")
        lines.append("|---|---|---|---|---|")
        for o in openings:
            lines.append(
                f"| {o.get('type', '')} | {o.get('orientation', '')} | "
                f"{o.get('area', 0)} m² | {o.get('u_value', '?')} | {o.get('g_value', '?')} |"
            )
        lines.append("")

    lines.append("---\n")
    lines.append("## Procédure Lesosai")
    lines.append("1. Ouvrir Lesosai, nouveau projet avec les paramètres du projet ci-dessus")
    lines.append("2. Sélectionner la station climatique (section 1)")
    lines.append("3. Saisir les zones thermiques (section 2)")
    lines.append("4. Créer les compositions selon les U-values (section 3)")
    lines.append("5. Reporter les ouvertures (section 4)")
    lines.append("6. Lancer le calcul, exporter le PDF")
    lines.append("7. Revenir dans BET Agent → Thermique → Importer les résultats")
    return "\n".join(lines)


def parse_lesosai_results_pdf(pdf_bytes: bytes) -> dict | None:
    """Extrait Qh, Qww, E, Qh_limite depuis un PDF rapport Lesosai.

    Best-effort via regex. Retourne None si l'extraction est insuffisante.
    """
    from app.services.pdf_extractor import extract_text_from_pdf

    text, _ = extract_text_from_pdf(pdf_bytes)
    if not text:
        return None

    def _find_number(patterns: list[str]) -> float | None:
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if m:
                try:
                    return float(m.group(1).replace("'", "").replace(",", ".").replace(" ", ""))
                except (ValueError, IndexError):
                    continue
        return None

    qh = _find_number([
        r"Qh[^=\n]{0,30}=?\s*([\d'.,]+)\s*MJ",
        r"besoin.*chauffage[^=\n]{0,40}([\d'.,]+)\s*MJ",
    ])
    qww = _find_number([
        r"Qww[^=\n]{0,30}=?\s*([\d'.,]+)\s*MJ",
        r"eau chaude[^=\n]{0,40}([\d'.,]+)\s*MJ",
    ])
    e = _find_number([
        r"E\s*[^=\n]{0,20}=?\s*([\d'.,]+)\s*MJ",
        r"énergie primaire[^=\n]{0,30}([\d'.,]+)\s*MJ",
    ])
    qh_limite = _find_number([
        r"Qh.?li[mw][^=\n]{0,20}=?\s*([\d'.,]+)\s*MJ",
        r"valeur limite[^=\n]{0,30}([\d'.,]+)\s*MJ",
    ])

    if not any([qh, qww, e]):
        return None

    return {
        "qh_mj_m2_an": qh or 0,
        "qww_mj_m2_an": qww or 0,
        "e_mj_m2_an": e or (qh or 0) + (qww or 0),
        "qh_limite_mj_m2_an": qh_limite,
        "compliant": (qh <= qh_limite) if (qh and qh_limite) else None,
        "extracted_from": "lesosai_pdf_export",
    }
