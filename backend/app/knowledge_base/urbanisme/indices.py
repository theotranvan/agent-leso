"""Indices urbanistiques par zone d'affectation — Vaud et Genève.

Source méthodologique : règlements communaux types, LATC (VD), LCI/LDTR (GE),
guide CAMAC. Ces indices sont des références indicatives qui DOIVENT être
validés au cas par cas avec le règlement communal applicable.

Utilité dans BET Agent :
  - Dossier de mise en enquête : calcul automatique IUS/IBUS/CUS, contrôle conformité
  - Contrôle réglementaire : alerte si dépassement
  - Simulation rapide : choix de la typologie selon zone
"""
from __future__ import annotations

from typing import Literal

# ==========================================================================
# DÉFINITIONS DES INDICES (SIA 416 / réglementaire suisse)
# ==========================================================================
"""
IUS — Indice d'Utilisation du Sol = SBP / surface terrain (SBP = surface brute de plancher)
IBUS — Indice Brut d'Utilisation du Sol = SBPu / surface terrain (SBPu = SBP utilisable)
ILE — Indice Linéaire d'Emprise au sol
ITE — Indice de Terrain Équivalent (zones densifiables)
CUS — Coefficient d'Utilisation du Sol (équivalent IUS dans certains cantons)
COS — Coefficient d'Occupation du Sol = emprise au sol / surface terrain
"""


# ==========================================================================
# VAUD — Zones d'affectation typiques
# ==========================================================================
# Source : LATC (Loi sur l'aménagement du territoire et les constructions),
# règlements communaux types (Lausanne, Vevey, Yverdon, Renens, etc.)

ZONES_VAUD = {
    "centre_ville": {
        "label": "Zone centre-ville / urbaine dense",
        "description": "Cœurs historiques, zones densifiées Lausanne / Vevey / Morges",
        "indices": {
            "IUS_max": 2.50,
            "IBUS_max": 3.20,
            "COS_max": 0.70,
            "hauteur_corniche_max_m": 18.0,
            "hauteur_faitage_max_m": 22.0,
            "nb_niveaux_max": 5,
        },
        "regles": [
            "Alignement obligatoire sur rue",
            "Distance aux limites variable selon orientation",
            "Cours intérieures et patios autorisés",
            "Toitures plates ou en pente selon caractère du quartier",
        ],
        "communes_exemples": ["Lausanne centre", "Vevey vieille ville", "Yverdon-les-Bains centre"],
    },
    "zone_habitation_forte_densite": {
        "label": "Zone d'habitation de forte densité",
        "description": "Immeubles collectifs 4-6 étages, périphérie urbaine dense",
        "indices": {
            "IUS_max": 1.50,
            "IBUS_max": 1.95,
            "COS_max": 0.45,
            "hauteur_corniche_max_m": 15.0,
            "hauteur_faitage_max_m": 18.0,
            "nb_niveaux_max": 4,
        },
        "regles": [
            "Distance limite parcelle ≥ H/2 (H = hauteur façade)",
            "Ratio espaces verts ≥ 25% surface terrain",
            "Stationnement : 1 place / 100 m² SBP logement",
        ],
        "communes_exemples": ["Lausanne quartiers", "Renens", "Pully", "Prilly"],
    },
    "zone_habitation_moyenne_densite": {
        "label": "Zone d'habitation de moyenne densité",
        "description": "Petits collectifs et villas mitoyennes, R+2 à R+3",
        "indices": {
            "IUS_max": 0.80,
            "IBUS_max": 1.05,
            "COS_max": 0.30,
            "hauteur_corniche_max_m": 10.5,
            "hauteur_faitage_max_m": 13.5,
            "nb_niveaux_max": 3,
        },
        "regles": [
            "Distance limite parcelle ≥ 6 m minimum",
            "Espaces verts ≥ 40% surface terrain",
            "Stationnement : 1.2 place / logement",
        ],
        "communes_exemples": ["Communes périurbaines lausannoises"],
    },
    "zone_habitation_faible_densite": {
        "label": "Zone d'habitation de faible densité (villas)",
        "description": "Maisons individuelles, R+1 à R+2",
        "indices": {
            "IUS_max": 0.45,
            "IBUS_max": 0.55,
            "COS_max": 0.20,
            "hauteur_corniche_max_m": 7.5,
            "hauteur_faitage_max_m": 10.5,
            "nb_niveaux_max": 2,
        },
        "regles": [
            "Distance limite parcelle ≥ 6 m",
            "Espaces verts ≥ 50% surface terrain",
            "Stationnement : 1.5-2 places / logement",
        ],
        "communes_exemples": ["Lutry", "Belmont", "Epalinges", "Pully villas"],
    },
    "zone_mixte": {
        "label": "Zone mixte habitation / activités",
        "description": "Cœurs de villages, zones permettant commerce et logement",
        "indices": {
            "IUS_max": 1.20,
            "IBUS_max": 1.55,
            "COS_max": 0.40,
            "hauteur_corniche_max_m": 12.0,
            "hauteur_faitage_max_m": 15.0,
            "nb_niveaux_max": 3,
        },
        "regles": [
            "Rez-de-chaussée commercial souvent imposé sur rue principale",
            "Logements en étages supérieurs",
        ],
    },
    "zone_artisanale": {
        "label": "Zone d'activités artisanales",
        "description": "Artisanat, petite industrie, pas de logement",
        "indices": {
            "IUS_max": 1.20,
            "IBUS_max": None,
            "COS_max": 0.55,
            "hauteur_corniche_max_m": 12.0,
            "hauteur_faitage_max_m": 14.0,
            "nb_niveaux_max": 3,
        },
        "regles": [
            "Pas de logement sauf gardiennage",
            "Stationnement : selon surface activité",
            "Quai de chargement obligatoire si activité de production",
        ],
    },
    "zone_industrielle": {
        "label": "Zone industrielle",
        "description": "Industrie, gros logistique",
        "indices": {
            "IUS_max": 1.50,
            "IBUS_max": None,
            "COS_max": 0.65,
            "hauteur_corniche_max_m": 15.0,
            "hauteur_faitage_max_m": 18.0,
        },
        "regles": [
            "Aucun logement autorisé",
            "Étude d'impact sur l'environnement souvent requise",
            "Distances renforcées selon nuisances",
        ],
    },
}


# ==========================================================================
# GENÈVE — Zones d'affectation (LCI + LDTR)
# ==========================================================================

ZONES_GENEVE = {
    "1e_zone": {
        "label": "1ʳᵉ zone (Vieille-Ville et zones historiques)",
        "description": "Périmètres protégés en surface, alignements imposés",
        "indices": {
            "IUS_max": 2.50,  # variable selon plan localisé
            "IBUS_max": None,  # ne s'applique pas, plan localisé
            "COS_max": 1.00,
            "hauteur_corniche_max_m": 21.0,
            "hauteur_faitage_max_m": 27.0,
            "nb_niveaux_max": 6,
        },
        "regles": [
            "LCI art. 1 et suivants : restrictions patrimoniales",
            "LDTR applicable (loi sur la démolition, transformation et rénovation)",
            "Préavis CMNS (Commission des monuments, de la nature et des sites)",
            "Alignement sur rue obligatoire",
        ],
    },
    "2e_zone": {
        "label": "2ᵉ zone (couronne urbaine)",
        "description": "Pâquis, Eaux-Vives, Plainpalais, Servette, Carouge",
        "indices": {
            "IUS_max": 2.50,
            "IBUS_max": None,
            "COS_max": 0.85,
            "hauteur_corniche_max_m": 21.0,
            "hauteur_faitage_max_m": 27.0,
            "nb_niveaux_max": 6,
        },
        "regles": [
            "LDTR applicable",
            "Maintien du logement (transformation logement → bureau interdite sans autorisation)",
            "Stationnement : selon règlement communal et plan directeur cantonal",
        ],
    },
    "3e_zone": {
        "label": "3ᵉ zone (zone urbaine dense)",
        "description": "Zones intermédiaires, immeubles 4-5 étages",
        "indices": {
            "IUS_max": 1.20,
            "IBUS_max": None,
            "COS_max": 0.50,
            "hauteur_corniche_max_m": 18.0,
            "hauteur_faitage_max_m": 21.0,
            "nb_niveaux_max": 5,
        },
        "regles": [
            "LDTR applicable",
            "Distances et gabarits selon LCI art. 27",
        ],
    },
    "4e_zone_a": {
        "label": "4ᵉ zone (zone résidentielle)",
        "description": "Banlieue résidentielle, petits collectifs et villas",
        "indices": {
            "IUS_max": 0.80,
            "IBUS_max": None,
            "COS_max": 0.40,
            "hauteur_corniche_max_m": 12.5,
            "hauteur_faitage_max_m": 15.0,
            "nb_niveaux_max": 3,
        },
        "regles": [
            "LDTR applicable si > 4 logements",
            "Distances aux limites : 6 m minimum",
        ],
    },
    "5e_zone": {
        "label": "5ᵉ zone (zone villas)",
        "description": "Villas individuelles, faible densité",
        "indices": {
            "IUS_max": 0.40,  # densification possible 0.48 selon LCI art. 59 al. 4
            "IBUS_max": None,
            "COS_max": 0.20,
            "hauteur_corniche_max_m": 8.5,
            "hauteur_faitage_max_m": 11.0,
            "nb_niveaux_max": 2,
        },
        "regles": [
            "Possibilité densification 0.48 voire 0.60 selon LCI art. 59 alinéa 4 (logement abordable)",
            "Distance aux limites : 5 m minimum, ou H/2 si > 10 m",
            "Toitures à pans imposées dans certains périmètres",
        ],
        "notes_specifiques": (
            "La densification en 5e zone (art. 59 al. 4 LCI) impose la création de "
            "logements à loyer maîtrisé ou à prix coûtant. Étude juridique préalable obligatoire."
        ),
    },
    "zone_industrielle": {
        "label": "Zone industrielle (loi sur les zones de développement industriel)",
        "description": "ZIPLO, ZIBAT, ZIMOGA, ZIBAY...",
        "indices": {
            "IUS_max": 1.50,
            "IBUS_max": None,
            "COS_max": 0.65,
            "hauteur_corniche_max_m": 15.0,
            "hauteur_faitage_max_m": 18.0,
        },
        "regles": [
            "Loi sur les ZID applicable",
            "Pas de logement (sauf logement de fonction strict)",
            "FTI (Fondation pour terrains industriels) gestionnaire éventuel",
        ],
    },
}


# ==========================================================================
# API D'ACCÈS
# ==========================================================================

Canton = Literal["VD", "GE", "NE", "FR", "VS", "JU"]


def get_zone_indices(canton: Canton, zone_key: str) -> dict | None:
    """Retourne les indices d'une zone d'affectation.

    Args:
        canton: "VD" ou "GE" (autres cantons à compléter)
        zone_key: identifiant de zone (ex: "5e_zone", "zone_habitation_forte_densite")

    Returns:
        Dict avec label, indices (IUS/IBUS/COS/hauteurs), règles. None si inconnu.
    """
    if canton == "VD":
        return ZONES_VAUD.get(zone_key)
    elif canton == "GE":
        return ZONES_GENEVE.get(zone_key)
    return None


def list_zones(canton: Canton) -> list[dict]:
    """Liste les zones disponibles pour un canton."""
    if canton == "VD":
        return [{"key": k, **v} for k, v in ZONES_VAUD.items()]
    elif canton == "GE":
        return [{"key": k, **v} for k, v in ZONES_GENEVE.items()]
    return []


def check_conformite_urbanistique(
    canton: Canton,
    zone_key: str,
    surface_terrain_m2: float,
    sbp_projetee_m2: float,
    emprise_sol_m2: float,
    hauteur_corniche_m: float,
    hauteur_faitage_m: float,
    nb_niveaux: int,
) -> dict:
    """Vérifie la conformité d'un projet aux indices de zone.

    Returns:
        Dict avec ius_projete, ibus_projete, cos_projete, conformite (booléens),
        depassements (liste des règles violées), zone_info.
    """
    zone = get_zone_indices(canton, zone_key)
    if not zone:
        return {"error": f"Zone inconnue : {zone_key} pour canton {canton}"}

    indices = zone["indices"]
    ius_projete = sbp_projetee_m2 / surface_terrain_m2 if surface_terrain_m2 else 0
    cos_projete = emprise_sol_m2 / surface_terrain_m2 if surface_terrain_m2 else 0

    depassements = []
    if indices.get("IUS_max") and ius_projete > indices["IUS_max"]:
        depassements.append({
            "regle": "IUS_max",
            "valeur_max": indices["IUS_max"],
            "valeur_projetee": round(ius_projete, 3),
            "depassement_pct": round((ius_projete / indices["IUS_max"] - 1) * 100, 1),
        })
    if indices.get("COS_max") and cos_projete > indices["COS_max"]:
        depassements.append({
            "regle": "COS_max",
            "valeur_max": indices["COS_max"],
            "valeur_projetee": round(cos_projete, 3),
            "depassement_pct": round((cos_projete / indices["COS_max"] - 1) * 100, 1),
        })
    if indices.get("hauteur_corniche_max_m") and hauteur_corniche_m > indices["hauteur_corniche_max_m"]:
        depassements.append({
            "regle": "hauteur_corniche_max_m",
            "valeur_max": indices["hauteur_corniche_max_m"],
            "valeur_projetee": hauteur_corniche_m,
        })
    if indices.get("hauteur_faitage_max_m") and hauteur_faitage_m > indices["hauteur_faitage_max_m"]:
        depassements.append({
            "regle": "hauteur_faitage_max_m",
            "valeur_max": indices["hauteur_faitage_max_m"],
            "valeur_projetee": hauteur_faitage_m,
        })
    if indices.get("nb_niveaux_max") and nb_niveaux > indices["nb_niveaux_max"]:
        depassements.append({
            "regle": "nb_niveaux_max",
            "valeur_max": indices["nb_niveaux_max"],
            "valeur_projetee": nb_niveaux,
        })

    return {
        "canton": canton,
        "zone": zone_key,
        "zone_label": zone["label"],
        "ius_projete": round(ius_projete, 3),
        "cos_projete": round(cos_projete, 3),
        "ius_max": indices.get("IUS_max"),
        "cos_max": indices.get("COS_max"),
        "surface_terrain_m2": surface_terrain_m2,
        "sbp_projetee_m2": sbp_projetee_m2,
        "emprise_sol_m2": emprise_sol_m2,
        "hauteur_corniche_m": hauteur_corniche_m,
        "hauteur_faitage_m": hauteur_faitage_m,
        "nb_niveaux": nb_niveaux,
        "conforme": len(depassements) == 0,
        "depassements": depassements,
        "regles_zone": zone["regles"],
        "note": "Indices indicatifs. Validation obligatoire avec règlement communal applicable.",
    }
