"""Extraction de l'enveloppe thermique depuis un fichier IFC.

Objectif : faire gagner ~1h par affaire à l'ingénieur. Au lieu de saisir
manuellement les surfaces d'enveloppe, les U-values et le volume dans Lesosai,
LESO lit la maquette IFC et pré-remplit ces données. L'ingénieur n'a plus
qu'à vérifier et corriger, pas à tout ressaisir.

Le résultat est un dictionnaire prêt à alimenter le justificatif SIA 380/1
(connecteur Lesosai gbXML) — avec un indicateur de complétude pour chaque champ,
pour que l'ingénieur sache exactement ce qui a été extrait vs ce qu'il doit
compléter à la main.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


# Correspondance type IFC → composant d'enveloppe SIA 380/1
IFC_TO_ENVELOPE = {
    "IfcWall": "murs_ext",
    "IfcCurtainWall": "murs_ext",
    "IfcRoof": "toiture",
    "IfcSlab": "plancher_bas",   # approximation : à affiner avec PredefinedType
    "IfcWindow": "fenetres",
    "IfcDoor": "fenetres",       # portes vitrées comptées avec les fenêtres
}

# U-values cibles par défaut (Minergie-P) si absentes de l'IFC — INDICATIVES
DEFAULT_U_MINERGIE_P = {
    "toiture": 0.12,
    "murs_ext": 0.14,
    "plancher_bas": 0.15,
    "fenetres": 0.80,
}


def extract_envelope_for_thermal(ifc_bytes: bytes) -> dict[str, Any]:
    """Extrait les données d'enveloppe thermique d'un IFC.

    Returns un dict avec, pour chaque composant : surface agrégée, U-value
    moyenne (si présente), source (ifc vs défaut), et un flag de complétude.
    """
    # Import paresseux : ifcopenshell n'est nécessaire qu'à l'exécution
    from app.services.ifc_parser import (
        extract_spaces_and_surfaces,
        extract_thermal_properties,
        parse_ifc_metadata,
    )

    metadata = parse_ifc_metadata(ifc_bytes)
    if metadata.get("error"):
        return {"error": metadata["error"], "extracted": False}

    thermal_elements = extract_thermal_properties(ifc_bytes)
    spaces = extract_spaces_and_surfaces(ifc_bytes)

    # Agrégation des surfaces et U-values par composant d'enveloppe
    surfaces = defaultdict(float)
    u_values = defaultdict(list)

    for el in thermal_elements:
        comp = IFC_TO_ENVELOPE.get(el["type"])
        if not comp:
            continue
        thermal = el.get("thermal_properties", {})
        # Surface : on cherche les quantités, sinon on ignore (l'IFC doit les porter)
        area = thermal.get("Area") or thermal.get("GrossArea") or thermal.get("NetArea")
        u = (
            thermal.get("ThermalTransmittance")
            or thermal.get("UValue")
            or thermal.get("U-Value")
        )
        if area:
            try:
                surfaces[comp] += float(area)
            except (ValueError, TypeError):
                pass
        if u:
            try:
                u_values[comp].append(float(u))
            except (ValueError, TypeError):
                pass

    # Volume chauffé : somme des volumes des espaces
    volume_m3 = 0.0
    sre_m2 = 0.0
    for sp in spaces:
        if sp.get("volume"):
            try:
                volume_m3 += float(sp["volume"])
            except (ValueError, TypeError):
                pass
        if sp.get("area"):
            try:
                sre_m2 += float(sp["area"])
            except (ValueError, TypeError):
                pass

    # Construction du résultat par composant
    components = {}
    completeness_score = 0
    total_fields = 0

    for comp in ("toiture", "murs_ext", "plancher_bas", "fenetres"):
        surf = round(surfaces.get(comp, 0), 1)
        us = u_values.get(comp, [])
        if us:
            u_mean = round(sum(us) / len(us), 3)
            u_src = "ifc"
        else:
            u_mean = DEFAULT_U_MINERGIE_P.get(comp)
            u_src = "défaut (à vérifier)"
        components[comp] = {
            "surface_m2": surf,
            "u_value": u_mean,
            "u_source": u_src,
            "surface_extracted": surf > 0,
            "u_extracted": bool(us),
        }
        total_fields += 2
        if surf > 0:
            completeness_score += 1
        if us:
            completeness_score += 1

    completeness_pct = round(completeness_score / total_fields * 100) if total_fields else 0

    # Liste des champs à compléter manuellement
    to_complete = []
    for comp, data in components.items():
        if not data["surface_extracted"]:
            to_complete.append(f"Surface {comp.replace('_', ' ')} (absente de l'IFC)")
        if not data["u_extracted"]:
            to_complete.append(f"U-value {comp.replace('_', ' ')} (valeur par défaut Minergie-P utilisée)")
    if volume_m3 == 0:
        to_complete.append("Volume chauffé (Qto_SpaceBaseQuantities absent)")
    if sre_m2 == 0:
        to_complete.append("SRE (surface de référence énergétique)")

    return {
        "extracted": True,
        "metadata": metadata,
        "sre_m2": round(sre_m2, 1),
        "volume_m3": round(volume_m3, 1),
        "components": components,
        "completeness_pct": completeness_pct,
        "to_complete": to_complete,
        "summary": (
            f"Enveloppe extraite à {completeness_pct}% depuis la maquette "
            f"({metadata.get('nb_spaces', 0)} espaces, "
            f"{len([e for e in thermal_elements])} éléments d'enveloppe). "
            + (f"{len(to_complete)} champ(s) à compléter manuellement."
               if to_complete else "Toutes les données nécessaires ont été extraites.")
        ),
    }
