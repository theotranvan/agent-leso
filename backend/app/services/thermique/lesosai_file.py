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

logger = logging.getLogger(__name__)


def serialize_to_lesosai_xml(thermal_model: dict) -> bytes:
    """Produit un XML interne structuré depuis un modèle thermique.

    Format interne LESO (pas Lesosai natif), lisible par un humain ou par le
    script RPA Lesosai de l'opérateur. Remplace l'ancienne fonction V2.
    """
    root = ET.Element("LesosaiExport", version="1.0", generator="LESO-V3")
    meta = ET.SubElement(root, "Meta")
    ET.SubElement(meta, "ExportedAt").text = datetime.utcnow().isoformat()
    ET.SubElement(meta, "Notice").text = (
        "Fichier intermédiaire. Format interne LESO — à ouvrir en parallèle de Lesosai."
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

    # Surface de référence énergétique (SRE) — saisie explicite ou somme des zones
    sre = (thermal_model.get("hypotheses") or {}).get("sre_m2")
    if not sre:
        sre = sum(float(z.get("area", 0) or 0) for z in (thermal_model.get("zones") or []))
    ET.SubElement(project, "SreM2").text = str(sre or "")

    # Parois
    walls_el = ET.SubElement(root, "Walls")
    for w in thermal_model.get("walls") or []:
        wall = ET.SubElement(walls_el, "Wall", id=str(w.get("id", "")))
        ET.SubElement(wall, "Type").text = str(w.get("type", "mur_exterieur"))
        ET.SubElement(wall, "Designation").text = str(w.get("name", "") or "")
        ET.SubElement(wall, "Orientation").text = str(w.get("orientation", "") or "")
        ET.SubElement(wall, "AreaM2").text = str(w.get("area", 0))
        ET.SubElement(wall, "UValueWm2K").text = str(w.get("u_value", "") or "")

    # Ouvertures
    openings_el = ET.SubElement(root, "Openings")
    for o in thermal_model.get("openings") or []:
        op = ET.SubElement(openings_el, "Opening", id=str(o.get("id", "")))
        ET.SubElement(op, "Type").text = str(o.get("type", "fenetre"))
        ET.SubElement(op, "Designation").text = str(o.get("name", "") or "")
        ET.SubElement(op, "Orientation").text = str(o.get("orientation", "") or "")
        ET.SubElement(op, "AreaM2").text = str(o.get("area", 0))
        ET.SubElement(op, "UValueWm2K").text = str(o.get("u_value", "") or "")
        ET.SubElement(op, "GValue").text = str(o.get("g_value", "") or "")

    # Ponts thermiques
    bridges_el = ET.SubElement(root, "ThermalBridges")
    for b in thermal_model.get("thermal_bridges") or []:
        br = ET.SubElement(bridges_el, "ThermalBridge")
        ET.SubElement(br, "Type").text = str(b.get("type", "") or "")
        ET.SubElement(br, "LengthM").text = str(b.get("length", 0))
        ET.SubElement(br, "PsiWmK").text = str(b.get("psi", "") or "")

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


_WALL_TYPE_LABELS = {
    "mur_exterieur": "Mur extérieur",
    "toiture": "Toiture",
    "dalle_sur_terrain": "Dalle sur terrain",
    "dalle_sur_exterieur": "Dalle sur extérieur",
    "dalle_sur_local_non_chauffe": "Dalle sur local non chauffé",
    "mur_contre_terre": "Mur contre terre",
    "mur_local_non_chauffe": "Mur contre local non chauffé",
    "plancher": "Plancher",
}
_OPENING_TYPE_LABELS = {
    "fenetre": "Fenêtre",
    "porte_vitree": "Porte vitrée",
    "porte_opaque": "Porte opaque",
}


def _wall_label(t: str) -> str:
    return _WALL_TYPE_LABELS.get(t, t or "—")


def _opening_label(t: str) -> str:
    return _OPENING_TYPE_LABELS.get(t, t or "—")


def _systems_lines(systems: dict) -> list[str]:
    """Bloc « installations techniques » de la fiche (chauffage / ventilation / ECS)."""
    if not isinstance(systems, dict) or not systems:
        return []
    lines: list[str] = ["## 5. Installations techniques"]
    heating = systems.get("heating") if isinstance(systems.get("heating"), dict) else None
    if heating:
        parts = []
        if heating.get("vector"):
            parts.append(f"vecteur **{heating['vector']}**")
        if heating.get("generator"):
            parts.append(f"générateur **{heating['generator']}**")
        if heating.get("efficiency"):
            parts.append(f"rendement {heating['efficiency']}")
        lines.append(f"- **Chauffage** : {', '.join(parts) if parts else 'à préciser'}")
    vent = systems.get("ventilation") if isinstance(systems.get("ventilation"), dict) else None
    if vent:
        parts = []
        if vent.get("type"):
            parts.append(f"type **{vent['type']}**")
        if vent.get("heat_recovery_pct") not in (None, ""):
            parts.append(f"récupération de chaleur {vent['heat_recovery_pct']} %")
        lines.append(f"- **Ventilation** : {', '.join(parts) if parts else 'à préciser'}")
    ecs = systems.get("ecs") if isinstance(systems.get("ecs"), dict) else None
    if ecs:
        parts = []
        if ecs.get("vector"):
            parts.append(f"vecteur **{ecs['vector']}**")
        if ecs.get("storage_liters") not in (None, ""):
            parts.append(f"stockage {ecs['storage_liters']} L")
        lines.append(f"- **Eau chaude sanitaire (ECS)** : {', '.join(parts) if parts else 'à préciser'}")
    lines.append("")
    return lines


def build_operator_sheet_markdown(thermal_model: dict, prepared: dict) -> str:
    """Fiche de saisie à ouvrir en parallèle de Lesosai pour reporter les données."""
    # SRE : valeur saisie explicitement, sinon estimée par la préparation du modèle.
    sre = (thermal_model.get("hypotheses") or {}).get("sre_m2") or prepared.get("sre_total_m2", 0)

    lines = ["# Fiche de saisie Lesosai", ""]
    lines.append(
        "> Document d'aide à la saisie. Reportez ces données dans Lesosai, lancez le "
        "calcul SIA 380/1, exportez le PDF de résultats puis réimportez-le dans LESO."
    )
    lines.append("")
    lines.append(f"**Projet** : {thermal_model.get('name', '?')}")
    lines.append(f"**Canton** : {thermal_model.get('canton', '?')}")
    lines.append(f"**Affectation** : {thermal_model.get('affectation', '?')}")
    lines.append(f"**Opération** : {thermal_model.get('operation_type', '?')}")
    lines.append(f"**Standard visé** : {thermal_model.get('standard', 'sia_380_1')}")
    lines.append(f"**SRE (surface de référence énergétique)** : {sre} m²")
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
        lines.append("## 3. Parois opaques")
        lines.append("| Désignation | Type | Orientation | Surface | U (W/m²·K) |")
        lines.append("|---|---|---|---|---|")
        for w in walls:
            lines.append(
                f"| {w.get('name', '') or '—'} | {_wall_label(w.get('type', ''))} | "
                f"{w.get('orientation', '') or '—'} | {w.get('area', 0)} m² | "
                f"{w.get('u_value', '?')} |"
            )
        lines.append("")

    openings = thermal_model.get("openings") or []
    if openings:
        lines.append("## 4. Ouvertures")
        lines.append("| Désignation | Type | Orientation | Surface | U | g |")
        lines.append("|---|---|---|---|---|---|")
        for o in openings:
            lines.append(
                f"| {o.get('name', '') or '—'} | {_opening_label(o.get('type', ''))} | "
                f"{o.get('orientation', '') or '—'} | {o.get('area', 0)} m² | "
                f"{o.get('u_value', '?')} | {o.get('g_value', '?')} |"
            )
        lines.append("")

    lines.extend(_systems_lines(thermal_model.get("systems") or {}))

    bridges = thermal_model.get("thermal_bridges") or []
    if bridges:
        lines.append("## 6. Ponts thermiques")
        lines.append("| Type de liaison | Longueur (ml) | ψ (W/m·K) |")
        lines.append("|---|---|---|")
        for b in bridges:
            lines.append(
                f"| {b.get('type', '') or '—'} | {b.get('length', 0)} | {b.get('psi', '?')} |"
            )
        lines.append("")

    lines.append("---\n")
    lines.append("## Procédure Lesosai")
    lines.append("1. Ouvrir Lesosai, nouveau projet avec les paramètres ci-dessus (canton, affectation, standard)")
    lines.append("2. Sélectionner la station climatique (section 1)")
    lines.append("3. Saisir les zones thermiques et la SRE (section 2)")
    lines.append("4. Créer les compositions de parois selon les désignations et U (section 3)")
    lines.append("5. Reporter les ouvertures avec U et facteur solaire g (section 4)")
    lines.append("6. Renseigner les installations techniques (section 5)")
    lines.append("7. Saisir les ponts thermiques (section 6)")
    lines.append("8. Lancer le calcul, exporter le PDF de résultats")
    lines.append("9. Revenir dans LESO → Thermique → Importer les résultats")
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
