"""Checklist incendie AEAI calibrée pratiques ECA Vaud + OCAS Genève.

Base : directives AEAI 1-15f, 10-15f, 15-15f, 17-15f (détection), 26-15f (sonorisation).
Calibrage : pratiques d'instruction ECA Vaud (Établissement cantonal d'assurance)
et OCAS Genève (Office cantonal des assurances sociales / Inspection des constructions).

Chaque item de checklist a :
  - reference_aeai : numéro d'article AEAI
  - critere : ce qui est vérifié
  - applicabilite : typologies et hauteurs concernées
  - documents_a_fournir : pièces à joindre au dossier
  - particularites_cantonales : différences ECA-VD vs OCAS-GE quand applicable
"""
from __future__ import annotations

from typing import Literal


# ==========================================================================
# CLASSIFICATION HAUTEUR (AEAI 10-15f)
# ==========================================================================

HAUTEURS_AEAI = {
    "faible": {"label": "Hauteur faible", "h_max_m": 11, "description": "≤ 11 m hauteur totale"},
    "moyenne": {"label": "Hauteur moyenne", "h_max_m": 30, "description": "11 < h ≤ 30 m"},
    "elevee": {"label": "Hauteur élevée", "h_max_m": 100, "description": "30 < h ≤ 100 m"},
    "tres_elevee": {"label": "Très grande hauteur", "h_max_m": None, "description": "> 100 m"},
}


# ==========================================================================
# CHECKLIST PAR TYPOLOGIE
# ==========================================================================

CHECKLIST_HABITATION_FAIBLE = {
    "typologie": "habitation_faible",
    "description": "Habitation, hauteur faible (≤ 11 m)",
    "categories": {
        "compartimentage": {
            "label": "Compartimentage incendie",
            "items": [
                {
                    "id": "comp_01",
                    "reference_aeai": "15-15f §3.3",
                    "critere": "Compartiments coupe-feu par logement (EI 60)",
                    "documents": ["Plans CF avec hachures coupe-feu", "Description matériaux"],
                    "particularites_VD": "ECA-VD : RF 1 minimum sur murs séparatifs entre logements",
                    "particularites_GE": "OCAS : conformité LCI art. 119, mêmes exigences",
                },
                {
                    "id": "comp_02",
                    "reference_aeai": "15-15f §3.5",
                    "critere": "Cages d'escalier en compartiment indépendant (EI 30)",
                    "documents": ["Coupe sur cage d'escalier", "Détails portes EI 30"],
                },
                {
                    "id": "comp_03",
                    "reference_aeai": "15-15f §3.7",
                    "critere": "Traversées de parois compartimentées calfeutrées RF 1",
                    "documents": ["Plan de calfeutrement", "Fiches techniques manchons CF"],
                },
            ],
        },
        "voies_evacuation": {
            "label": "Voies d'évacuation",
            "items": [
                {
                    "id": "evac_01",
                    "reference_aeai": "16-15f §2.1",
                    "critere": "Longueur maximale voie d'évacuation : 35 m",
                    "documents": ["Plan d'évacuation avec cotes"],
                },
                {
                    "id": "evac_02",
                    "reference_aeai": "16-15f §3.2",
                    "critere": "Largeur minimale 1.20 m, marches conformes",
                    "documents": ["Plan dimensions escaliers et couloirs"],
                },
                {
                    "id": "evac_03",
                    "reference_aeai": "17-15f §4",
                    "critere": "Éclairage de sécurité présent en circulations communes",
                    "documents": ["Schéma éclairage sécurité"],
                    "particularites_VD": "ECA-VD : autonomie ≥ 1h pour habitation",
                },
            ],
        },
        "detection_alarme": {
            "label": "Détection et alarme",
            "items": [
                {
                    "id": "det_01",
                    "reference_aeai": "20-15f §2.3",
                    "critere": "Détecteurs de fumée dans chaque logement (couloir + chambres)",
                    "documents": ["Plan d'implantation détecteurs"],
                    "particularites_VD": "ECA-VD recommande mais pas obligatoire en habitation faible",
                    "particularites_GE": "OCAS : exigé en zones 1ʳᵉ et 2ᵉ depuis 2018",
                },
            ],
        },
        "moyens_extinction": {
            "label": "Moyens d'extinction",
            "items": [
                {
                    "id": "ext_01",
                    "reference_aeai": "18-15f §3.1",
                    "critere": "Extincteurs portatifs accessibles (recommandé pour habitation faible)",
                    "documents": ["Plan implantation extincteurs"],
                },
                {
                    "id": "ext_02",
                    "reference_aeai": "21-15f",
                    "critere": "Accès des sapeurs-pompiers (route, façades)",
                    "documents": ["Plan d'accès, distances bouches d'incendie"],
                },
            ],
        },
    },
}

CHECKLIST_HABITATION_MOYENNE = {
    "typologie": "habitation_moyenne",
    "description": "Habitation, hauteur moyenne (11-30 m)",
    "categories": {
        "compartimentage": {
            "label": "Compartimentage incendie",
            "items": [
                {
                    "id": "comp_01",
                    "reference_aeai": "15-15f §3.3",
                    "critere": "Compartiments par logement EI 60 (incombustibles si > 22 m)",
                    "documents": ["Plans CF", "Justificatif réaction au feu matériaux"],
                    "particularites_VD": "ECA-VD : enveloppe RF 1 obligatoire au-dessus de 22 m",
                },
                {
                    "id": "comp_02",
                    "reference_aeai": "15-15f §3.5",
                    "critere": "Cage d'escalier protégée EI 60 + sas (au-dessus de 22 m)",
                    "documents": ["Coupe cage escalier", "Détail sas + portes EI 60"],
                },
                {
                    "id": "comp_03",
                    "reference_aeai": "15-15f §3.8",
                    "critere": "Façades RF 1 et limitation propagation par les façades",
                    "documents": ["Coupe façade", "Détail acrotère et brise-feu"],
                },
            ],
        },
        "voies_evacuation": {
            "label": "Voies d'évacuation",
            "items": [
                {
                    "id": "evac_01",
                    "reference_aeai": "16-15f §2.1",
                    "critere": "Deux issues indépendantes si plus de 50 personnes par étage",
                    "documents": ["Plan d'évacuation avec calculs effectifs"],
                },
                {
                    "id": "evac_02",
                    "reference_aeai": "16-15f §3.2",
                    "critere": "Cages d'escalier en surpression au-dessus de 22 m",
                    "documents": ["Étude de mise en surpression", "Schéma désenfumage"],
                },
            ],
        },
        "detection_alarme": {
            "label": "Détection et alarme",
            "items": [
                {
                    "id": "det_01",
                    "reference_aeai": "20-15f §2.4",
                    "critere": "Installation de détection incendie obligatoire dans parties communes",
                    "documents": ["Schéma DI EN 54 avec centrale et liaisons"],
                    "particularites_VD": "ECA-VD : raccordement obligatoire centre transmission",
                },
                {
                    "id": "det_02",
                    "reference_aeai": "20-15f §3.2",
                    "critere": "Détecteurs autonomes dans chaque logement (depuis 2015)",
                    "documents": ["Plan implantation détecteurs autonomes"],
                },
            ],
        },
        "desenfumage": {
            "label": "Désenfumage",
            "items": [
                {
                    "id": "des_01",
                    "reference_aeai": "21-15f §4.5",
                    "critere": "Désenfumage des cages d'escalier (exutoire min 5% surface cage)",
                    "documents": ["Plan exutoires", "Calcul surfaces désenfumage"],
                    "particularites_VD": "Exutoires SHEV à commande automatique au-dessus de 22 m",
                },
            ],
        },
        "moyens_extinction": {
            "label": "Moyens d'extinction et accès pompiers",
            "items": [
                {
                    "id": "ext_01",
                    "reference_aeai": "18-15f §3.2",
                    "critere": "Postes incendie intérieurs (RIA) au-dessus de 22 m",
                    "documents": ["Plan implantation RIA, dimensionnement"],
                },
                {
                    "id": "ext_02",
                    "reference_aeai": "21-15f §5",
                    "critere": "Colonne sèche pour bâtiments > 22 m",
                    "documents": ["Schéma colonne sèche, prise de raccord pompiers"],
                },
                {
                    "id": "ext_03",
                    "reference_aeai": "21-15f §6",
                    "critere": "Place de travail pompiers + bouche incendie ≤ 80 m",
                    "documents": ["Plan d'accès pompiers + bouches existantes"],
                },
            ],
        },
    },
}

CHECKLIST_HABITATION_ELEVEE = {
    "typologie": "habitation_elevee",
    "description": "Habitation, hauteur élevée (30-100 m)",
    "categories": {
        "compartimentage": {
            "label": "Compartimentage renforcé",
            "items": [
                {
                    "id": "comp_01",
                    "reference_aeai": "10-15f §3.2",
                    "critere": "Compartiments EI 90, matériaux RF 1 obligatoires",
                    "documents": ["Plans CF", "Tous PV de réaction au feu"],
                },
                {
                    "id": "comp_02",
                    "reference_aeai": "10-15f §4",
                    "critere": "Cage d'escalier de sécurité avec sas en surpression",
                    "documents": ["Étude surpression validée", "Coupes détaillées"],
                },
                {
                    "id": "comp_03",
                    "reference_aeai": "10-15f §5.3",
                    "critere": "Ascenseur pompiers EI 90",
                    "documents": ["Spécifications ascenseur", "PV essais"],
                },
            ],
        },
        "sprinkler": {
            "label": "Installation sprinkler",
            "items": [
                {
                    "id": "spk_01",
                    "reference_aeai": "19-15f",
                    "critere": "Installation sprinkler complète obligatoire",
                    "documents": ["Étude hydraulique", "Plans détaillés", "PV essais constructeur"],
                    "particularites_VD": "ECA-VD : validation par expert ECA agréé",
                },
            ],
        },
        "detection_alarme": {
            "label": "Détection et évacuation",
            "items": [
                {
                    "id": "det_01",
                    "reference_aeai": "20-15f §2.6",
                    "critere": "DI EN 54 complète, raccordée centre transmission",
                    "documents": ["Schéma complet DI"],
                },
                {
                    "id": "det_02",
                    "reference_aeai": "26-15f",
                    "critere": "Sonorisation d'évacuation EN 54-16",
                    "documents": ["Étude sonorisation", "Calcul intelligibilité STI"],
                },
            ],
        },
    },
}

CHECKLIST_ERP_MOYEN = {
    "typologie": "erp_moyen",
    "description": "Établissement recevant du public, 100-1000 personnes",
    "categories": {
        "effectifs": {
            "label": "Calcul des effectifs",
            "items": [
                {
                    "id": "eff_01",
                    "reference_aeai": "16-15f Annexe",
                    "critere": "Calcul effectif maximal par local selon table AEAI",
                    "documents": ["Tableau effectifs par local et par étage"],
                },
            ],
        },
        "evacuation": {
            "label": "Évacuation",
            "items": [
                {
                    "id": "evac_01",
                    "reference_aeai": "16-15f §2.3",
                    "critere": "Deux issues indépendantes obligatoires",
                    "documents": ["Plans d'évacuation"],
                },
                {
                    "id": "evac_02",
                    "reference_aeai": "16-15f §3.4",
                    "critere": "Largeur des issues : 1 unité de passage par 100 personnes",
                    "documents": ["Plan dimensionné", "Calcul UP par issue"],
                },
            ],
        },
        "detection": {
            "label": "Détection et alarme",
            "items": [
                {
                    "id": "det_01",
                    "reference_aeai": "20-15f §2.5",
                    "critere": "DI EN 54 + raccordement centre transmission",
                    "documents": ["Schéma DI complet"],
                    "particularites_VD": "ECA-VD : validation projet préalable obligatoire",
                    "particularites_GE": "OCAS : conformité art. 12 LCI complémentaire",
                },
                {
                    "id": "det_02",
                    "reference_aeai": "26-15f",
                    "critere": "Sonorisation d'évacuation si effectif > 300",
                    "documents": ["Étude sonorisation avec calcul STI"],
                },
            ],
        },
        "desenfumage": {
            "label": "Désenfumage",
            "items": [
                {
                    "id": "des_01",
                    "reference_aeai": "21-15f §4",
                    "critere": "Désenfumage des locaux > 1000 m² ou sous-sol",
                    "documents": ["Étude désenfumage", "Calcul surfaces aérauliques"],
                },
            ],
        },
        "sprinkler": {
            "label": "Sprinkler",
            "items": [
                {
                    "id": "spk_01",
                    "reference_aeai": "19-15f §2.2",
                    "critere": "Sprinkler obligatoire si surface > 2400 m² par compartiment",
                    "documents": ["Étude sprinkler complète si applicable"],
                },
            ],
        },
    },
}

CHECKLIST_PARKING_SOUTERRAIN = {
    "typologie": "parking_souterrain",
    "description": "Parking souterrain",
    "categories": {
        "ventilation": {
            "label": "Ventilation",
            "items": [
                {
                    "id": "vent_01",
                    "reference_aeai": "15-15f §4.4",
                    "critere": "Ventilation mécanique 6 vol/h, capteurs CO + détection",
                    "documents": ["Étude aéraulique", "Schéma CTA et capteurs"],
                },
                {
                    "id": "vent_02",
                    "reference_aeai": "21-15f §4.7",
                    "critere": "Ventilation de désenfumage en cas d'incendie",
                    "documents": ["Étude désenfumage + scénarios"],
                },
            ],
        },
        "compartimentage": {
            "label": "Compartimentage",
            "items": [
                {
                    "id": "comp_01",
                    "reference_aeai": "15-15f §4.3",
                    "critere": "Compartiments ≤ 2400 m² (au-delà = sprinkler obligatoire)",
                    "documents": ["Plan compartimentage avec surfaces"],
                },
                {
                    "id": "comp_02",
                    "reference_aeai": "15-15f §4.5",
                    "critere": "Sas d'accès EI 30 entre parking et bâtiment habité",
                    "documents": ["Détails sas et portes coupe-feu"],
                },
            ],
        },
        "evacuation": {
            "label": "Évacuation",
            "items": [
                {
                    "id": "evac_01",
                    "reference_aeai": "16-15f §2.6",
                    "critere": "Distance maximale 35 m à une issue",
                    "documents": ["Plan d'évacuation parking"],
                },
            ],
        },
        "vehicules_electriques": {
            "label": "Bornes véhicules électriques",
            "items": [
                {
                    "id": "ve_01",
                    "reference_aeai": "Note technique AEAI 2023",
                    "critere": "Bornes VE : étude spécifique de risque, séparation compartiments",
                    "documents": ["Étude risque bornes VE", "Plan implantation"],
                    "particularites_VD": "ECA-VD : exigence renforcée depuis 2024, validation projet",
                },
            ],
        },
    },
}


# ==========================================================================
# REGISTRE
# ==========================================================================

CHECKLISTS_AEAI = {
    "habitation_faible": CHECKLIST_HABITATION_FAIBLE,
    "habitation_moyenne": CHECKLIST_HABITATION_MOYENNE,
    "habitation_elevee": CHECKLIST_HABITATION_ELEVEE,
    "erp_moyen": CHECKLIST_ERP_MOYEN,
    "parking_souterrain": CHECKLIST_PARKING_SOUTERRAIN,
}


def get_checklist_aeai(typologie: str, canton: str | None = None) -> dict | None:
    """Retourne la checklist AEAI pour une typologie + canton.

    Args:
        typologie: "habitation_faible", "erp_moyen", "parking_souterrain"...
        canton: "VD" ou "GE" pour récupérer les particularités cantonales

    Returns:
        Checklist enrichie avec particularités cantonales si fournies.
    """
    cl = CHECKLISTS_AEAI.get(typologie)
    if not cl:
        return None

    # Si canton fourni, on inline les particularités
    if canton in ("VD", "GE"):
        cl_copy = {**cl, "canton_specifique": canton}
        # On rend les particularités plus visibles
        for cat in cl_copy["categories"].values():
            for item in cat["items"]:
                key = f"particularites_{canton}"
                if key in item:
                    item["particularites_canton"] = item[key]
        return cl_copy

    return cl


def list_typologies() -> list[str]:
    return list(CHECKLISTS_AEAI.keys())


def count_items_in_checklist(typologie: str) -> int:
    cl = CHECKLISTS_AEAI.get(typologie)
    if not cl:
        return 0
    return sum(len(cat["items"]) for cat in cl["categories"].values())
