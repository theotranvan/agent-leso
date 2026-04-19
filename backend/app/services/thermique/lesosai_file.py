"""Moteur Lesosai en mode FICHIER (scénario B du plan V2).

Génère un fichier XML structuré contenant le maximum de données du modèle thermique
+ un document de saisie opérateur (PDF) expliquant ce qui reste à compléter dans Lesosai.

IMPORTANT : le format exact du fichier projet Lesosai n'est pas publiquement documenté.
Ce module produit un format **générique interne** + une fiche de saisie.
Une fois le format Lesosai qualifié avec E4tech, on adapte `serialize_to_lesosai_xml()`.
"""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from app.services.thermique.engine_interface import ThermalEngine, ThermalEngineResult

logger = logging.getLogger(__name__)


class LesosaiFileEngine(ThermalEngine):
    """Génère un dossier de saisie Lesosai (XML interne + fiche opérateur).

    Pipeline :
      1. submit() produit un fichier XML + une fiche PDF de saisie
      2. L'utilisateur ouvre Lesosai, reprend les valeurs de la fiche, lance le calcul
      3. L'utilisateur uploade le PDF de résultats Lesosai
      4. On extrait les valeurs clés du PDF Lesosai avec parse_lesosai_results()
    """

    name = "lesosai_file"

    async def prepare_model(self, thermal_model: dict) -> dict:
        """Vérifie que le modèle est exploitable et génère les warnings."""
        warnings = []
        zones = thermal_model.get("zones") or []
        walls = thermal_model.get("walls") or []
        openings = thermal_model.get("openings") or []
        systems = thermal_model.get("systems") or {}

        if not zones:
            warnings.append("Aucune zone thermique - impossible de générer le dossier Lesosai")
        if not walls:
            warnings.append("Aucune paroi - saisie Lesosai très partielle")
        if not systems.get("heating"):
            warnings.append("Pas de système de chauffage spécifié - à saisir manuellement dans Lesosai")
        if not systems.get("ventilation"):
            warnings.append("Pas de ventilation spécifiée - à saisir manuellement dans Lesosai")

        total_area = sum(z.get("area", 0) for z in zones)

        return {
            "model": thermal_model,
            "warnings": warnings,
            "sre_total_m2": total_area,
            "ready_for_lesosai": len(walls) > 0 and total_area > 0,
        }

    async def submit(self, payload: dict) -> str:
        """Retourne un identifiant d'export. Le fichier est produit par serialize().

        Le vrai travail (sérialisation XML + fiche PDF) est exécuté par les fonctions
        de ce module, pas ici. submit() se contente de marquer l'export.
        """
        return f"lesosai_file_export_{datetime.utcnow().timestamp()}"

    async def fetch_results(self, job_id: str) -> ThermalEngineResult | None:
        """Le retour de résultats est asynchrone côté utilisateur.
        fetch_results retournera les valeurs APRÈS parsing du PDF Lesosai.
        Ici on renvoie None - c'est l'endpoint /import-results qui fait le travail.
        """
        return None

    def is_synchronous(self) -> bool:
        return False


def serialize_to_lesosai_xml(thermal_model: dict) -> bytes:
    """Produit un XML interne structuré contenant tout le modèle thermique.

    Format interne BET Agent (pas Lesosai natif). Une fois le format officiel Lesosai
    qualifié avec E4tech, on modifie cette fonction pour produire directement le .les.
    """
    root = ET.Element("LesosaiExport", version="1.0", generator="BET-Agent-V2")
    ET.SubElement(root, "Meta").text = ""
    meta = root.find("Meta")
    ET.SubElement(meta, "ExportedAt").text = datetime.utcnow().isoformat()
    ET.SubElement(meta, "Notice").text = (
        "Fichier intermédiaire destiné à guider la saisie dans Lesosai. "
        "Format interne BET Agent ; non natif Lesosai."
    )

    project = ET.SubElement(root, "Project")
    ET.SubElement(project, "Name").text = thermal_model.get("name", "Projet")
    ET.SubElement(project, "Canton").text = thermal_model.get("canton", "")
    ET.SubElement(project, "Affectation").text = thermal_model.get("affectation", "")
    ET.SubElement(project, "OperationType").text = thermal_model.get("operation_type", "")
    ET.SubElement(project, "Standard").text = thermal_model.get("standard", "sia_380_1")

    # Climat
    climate = thermal_model.get("climate") or {}
    if climate:
        clim = ET.SubElement(project, "Climate")
        for k, v in climate.items():
            ET.SubElement(clim, k).text = str(v)

    # Zones thermiques
    zones_el = ET.SubElement(root, "Zones")
    for z in thermal_model.get("zones") or []:
        zone = ET.SubElement(zones_el, "Zone", id=str(z.get("id", "")))
        ET.SubElement(zone, "Name").text = z.get("name", "")
        ET.SubElement(zone, "Affectation").text = z.get("affectation", thermal_model.get("affectation", ""))
        ET.SubElement(zone, "AreaM2").text = str(z.get("area", 0))
        ET.SubElement(zone, "VolumeM3").text = str(z.get("volume", 0))
        ET.SubElement(zone, "TempSetpointC").text = str(z.get("temp_setpoint", 20))

    # Parois
    walls_el = ET.SubElement(root, "Walls")
    for w in thermal_model.get("walls") or []:
        wall = ET.SubElement(walls_el, "Wall", id=str(w.get("id", "")))
        ET.SubElement(wall, "Type").text = w.get("type", "mur_exterieur")
        ET.SubElement(wall, "Orientation").text = w.get("orientation", "")
        ET.SubElement(wall, "AreaM2").text = str(w.get("area", 0))
        ET.SubElement(wall, "UValueWm2K").text = str(w.get("u_value", ""))
        layers_el = ET.SubElement(wall, "Layers")
        for layer in (w.get("layers") or []):
            la = ET.SubElement(layers_el, "Layer")
            ET.SubElement(la, "Material").text = layer.get("material", "")
            ET.SubElement(la, "ThicknessM").text = str(layer.get("thickness", ""))
            ET.SubElement(la, "LambdaWmK").text = str(layer.get("lambda", ""))

    # Ouvertures
    openings_el = ET.SubElement(root, "Openings")
    for o in thermal_model.get("openings") or []:
        op = ET.SubElement(openings_el, "Opening", id=str(o.get("id", "")))
        ET.SubElement(op, "Type").text = o.get("type", "fenetre")
        ET.SubElement(op, "AreaM2").text = str(o.get("area", 0))
        ET.SubElement(op, "UValueWm2K").text = str(o.get("u_value", ""))
        ET.SubElement(op, "GValue").text = str(o.get("g_value", ""))
        ET.SubElement(op, "Orientation").text = o.get("orientation", "")

    # Ponts thermiques
    bridges_el = ET.SubElement(root, "ThermalBridges")
    for b in thermal_model.get("thermal_bridges") or []:
        br = ET.SubElement(bridges_el, "Bridge")
        ET.SubElement(br, "Type").text = b.get("type", "")
        ET.SubElement(br, "LengthM").text = str(b.get("length", 0))
        ET.SubElement(br, "PsiWmK").text = str(b.get("psi", ""))

    # Systèmes
    systems_el = ET.SubElement(root, "Systems")
    systems_data = thermal_model.get("systems") or {}
    for system_name, system_data in systems_data.items():
        sys_el = ET.SubElement(systems_el, system_name.capitalize())
        if isinstance(system_data, dict):
            for k, v in system_data.items():
                ET.SubElement(sys_el, k).text = str(v) if v is not None else ""

    # Hypothèses overrides
    hypotheses_el = ET.SubElement(root, "Hypotheses")
    for k, v in (thermal_model.get("hypotheses") or {}).items():
        h = ET.SubElement(hypotheses_el, "Override", key=str(k))
        h.text = str(v)

    xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_str


def build_operator_sheet_markdown(thermal_model: dict, prepared: dict) -> str:
    """Génère une fiche de saisie opérateur en markdown.

    L'opérateur ouvre cette fiche en parallèle de Lesosai et reporte les valeurs écran par écran.
    """
    md = ["# Fiche de saisie Lesosai\n"]
    md.append(f"**Projet** : {thermal_model.get('name', '?')}")
    md.append(f"**Canton** : {thermal_model.get('canton', '?')}")
    md.append(f"**Affectation** : {thermal_model.get('affectation', '?')}")
    md.append(f"**Opération** : {thermal_model.get('operation_type', '?')}")
    md.append(f"**Standard visé** : {thermal_model.get('standard', 'sia_380_1')}")
    md.append(f"**SRE totale** : {prepared.get('sre_total_m2', 0):.1f} m²\n")

    if prepared.get("warnings"):
        md.append("## ⚠ Points d'attention")
        for w in prepared["warnings"]:
            md.append(f"- {w}")
        md.append("")

    # Climat
    climate = thermal_model.get("climate") or {}
    if climate:
        md.append("## 1. Station climatique / Climat")
        for k, v in climate.items():
            md.append(f"- **{k}** : {v}")
        md.append("")

    # Zones
    zones = thermal_model.get("zones") or []
    if zones:
        md.append("## 2. Zones thermiques")
        md.append("| Nom | Affectation | Surface m² | Volume m³ | T consigne °C |")
        md.append("|---|---|---|---|---|")
        for z in zones:
            md.append(f"| {z.get('name', '')} | {z.get('affectation', '')} | "
                      f"{z.get('area', 0)} | {z.get('volume', 0)} | {z.get('temp_setpoint', 20)} |")
        md.append("")

    # Parois
    walls = thermal_model.get("walls") or []
    if walls:
        md.append("## 3. Parois opaques")
        md.append("| Type | Orientation | Surface m² | U W/m²K |")
        md.append("|---|---|---|---|")
        for w in walls:
            md.append(f"| {w.get('type', '')} | {w.get('orientation', '')} | "
                      f"{w.get('area', 0)} | {w.get('u_value', '?')} |")
        md.append("")
        md.append("### Détail des couches (si composition fournie)")
        for w in walls:
            layers = w.get("layers") or []
            if layers:
                md.append(f"**{w.get('type', '')} - {w.get('orientation', '')}** :")
                for la in layers:
                    md.append(f"  - {la.get('material', '?')} : épaisseur "
                              f"{la.get('thickness', '?')} m, λ={la.get('lambda', '?')} W/mK")
        md.append("")

    # Ouvertures
    openings = thermal_model.get("openings") or []
    if openings:
        md.append("## 4. Ouvertures (fenêtres, portes vitrées)")
        md.append("| Type | Orientation | Surface m² | U W/m²K | g |")
        md.append("|---|---|---|---|---|")
        for o in openings:
            md.append(f"| {o.get('type', '')} | {o.get('orientation', '')} | "
                      f"{o.get('area', 0)} | {o.get('u_value', '?')} | {o.get('g_value', '?')} |")
        md.append("")

    # Ponts thermiques
    bridges = thermal_model.get("thermal_bridges") or []
    if bridges:
        md.append("## 5. Ponts thermiques")
        md.append("| Type | Longueur m | ψ W/mK |")
        md.append("|---|---|---|")
        for b in bridges:
            md.append(f"| {b.get('type', '')} | {b.get('length', 0)} | {b.get('psi', '?')} |")
        md.append("")

    # Systèmes
    systems = thermal_model.get("systems") or {}
    if systems:
        md.append("## 6. Systèmes techniques")
        for sys_name, sys_data in systems.items():
            md.append(f"### {sys_name.capitalize()}")
            if isinstance(sys_data, dict):
                for k, v in sys_data.items():
                    md.append(f"- **{k}** : {v}")
            md.append("")

    md.append("---\n")
    md.append("## Étapes de saisie recommandées dans Lesosai")
    md.append("1. Créer un nouveau projet Lesosai avec les informations projet ci-dessus")
    md.append("2. Sélectionner la station climatique indiquée en section 1")
    md.append("3. Saisir les zones thermiques (section 2) une à une")
    md.append("4. Créer les compositions de parois selon section 3 (onglet Constructions)")
    md.append("5. Reporter les ouvertures (section 4)")
    md.append("6. Saisir les ponts thermiques (section 5)")
    md.append("7. Configurer les systèmes techniques (section 6)")
    md.append("8. Lancer le calcul, exporter le rapport PDF Lesosai")
    md.append("9. Revenir dans BET Agent → Thermique → Importer les résultats")
    md.append("")
    md.append("**Temps de saisie estimé** : 1-3 h pour un projet standard avec cette fiche, "
              "contre 6-16 h sans.\n")

    return "\n".join(md)


def parse_lesosai_results_pdf(pdf_bytes: bytes) -> dict | None:
    """Extrait les valeurs clés d'un rapport PDF Lesosai.

    Cherche Qh, Qww, E, Qh_limite dans le texte. Best-effort.
    Retourne None si extraction insuffisante.
    """
    import re

    from app.services.pdf_extractor import extract_text_from_pdf

    text, _ = extract_text_from_pdf(pdf_bytes)
    if not text:
        return None

    def _find_value(patterns: list[str]) -> float | None:
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if m:
                try:
                    return float(m.group(1).replace(",", ".").replace("'", "").replace(" ", ""))
                except (ValueError, IndexError):
                    continue
        return None

    qh = _find_value([
        r"Qh[^=\n]{0,30}=?\s*([\d'.,]+)\s*MJ",
        r"besoin.*chauffage[^=\n]{0,40}([\d'.,]+)\s*MJ",
        r"Qh.*?:?\s*([\d'.,]+)",
    ])
    qww = _find_value([
        r"Qww[^=\n]{0,30}=?\s*([\d'.,]+)\s*MJ",
        r"eau chaude[^=\n]{0,40}([\d'.,]+)\s*MJ",
    ])
    e = _find_value([
        r"E\s*[^=\n]{0,20}=?\s*([\d'.,]+)\s*MJ",
        r"énergie primaire[^=\n]{0,30}([\d'.,]+)\s*MJ",
    ])
    qh_limite = _find_value([
        r"Qh.?li[mw][^=\n]{0,20}=?\s*([\d'.,]+)\s*MJ",
        r"valeur limite[^=\n]{0,30}([\d'.,]+)\s*MJ",
    ])

    if not (qh or qww or e):
        return None

    return {
        "qh_mj_m2_an": qh or 0,
        "qww_mj_m2_an": qww or 0,
        "e_mj_m2_an": e or (qh or 0) + (qww or 0),
        "qh_limite_mj_m2_an": qh_limite,
        "compliant": (qh <= qh_limite) if (qh and qh_limite) else None,
        "extracted_from": "lesosai_pdf_export",
    }
