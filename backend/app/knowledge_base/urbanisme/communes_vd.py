"""Règlements communaux vaudois — indices par commune et zone.

Complète le module indices.py générique avec des données par COMMUNE,
car en Vaud les indices sont fixés par le règlement communal (PGA / PACom),
pas seulement par le type de zone cantonal.

Source méthodologique : règlements communaux types des principales communes
de l'agglomération lausannoise (zone d'activité probable d'un BET vaudois).
Indices indicatifs à valider avec le règlement en vigueur de la commune.

ATTENTION : ces valeurs évoluent avec les révisions de PGA. Toujours vérifier
la version en vigueur auprès de la commune ou sur le guichet cantonal.
"""
from __future__ import annotations


# Indices par commune → zone communale.
# IUS = indice d'utilisation du sol, COS = coefficient d'occupation du sol.
COMMUNES_VD = {
    "lausanne": {
        "label": "Lausanne",
        "reference_reglement": "RPGA Lausanne (Règlement du plan général d'affectation)",
        "zones": {
            "centre_ville": {
                "label": "Zone urbaine de forte densité (centre)",
                "IUS_max": 2.5, "COS_max": 0.7,
                "hauteur_corniche_max_m": 18.0, "hauteur_faitage_max_m": 22.0,
                "nb_niveaux_max": 6,
                "stationnement": "Selon plan directeur stationnement : réduction possible centre-ville",
                "notes": "Périmètres ISOS protégés, préavis Déléguée au patrimoine bâti.",
            },
            "moyenne_densite": {
                "label": "Zone mixte de moyenne densité",
                "IUS_max": 1.0, "COS_max": 0.5,
                "hauteur_corniche_max_m": 13.5, "hauteur_faitage_max_m": 16.5,
                "nb_niveaux_max": 4,
                "stationnement": "1 place / 100 m² SBP logement, réduction en zone bien desservie TP",
            },
            "faible_densite": {
                "label": "Zone de villas",
                "IUS_max": 0.5, "COS_max": 0.25,
                "hauteur_corniche_max_m": 7.5, "hauteur_faitage_max_m": 10.5,
                "nb_niveaux_max": 2,
                "stationnement": "2 places / logement",
            },
        },
    },
    "renens": {
        "label": "Renens",
        "reference_reglement": "RCATC Renens",
        "zones": {
            "centre": {
                "label": "Zone de centre (densification axe gare-Closel)",
                "IUS_max": 2.0, "COS_max": 0.6,
                "hauteur_corniche_max_m": 16.5, "hauteur_faitage_max_m": 19.5,
                "nb_niveaux_max": 5,
                "stationnement": "0.8 place / logement (zone très bien desservie TP, M1/CFF)",
                "notes": "Secteur PALM, exigences de mixité et qualité urbaine renforcées.",
            },
            "habitation_collective": {
                "label": "Zone d'habitation collective",
                "IUS_max": 1.2, "COS_max": 0.4,
                "hauteur_corniche_max_m": 13.5, "hauteur_faitage_max_m": 16.0,
                "nb_niveaux_max": 4,
                "stationnement": "1 place / logement",
            },
        },
    },
    "prilly": {
        "label": "Prilly",
        "reference_reglement": "RCAT Prilly",
        "zones": {
            "moyenne_densite": {
                "label": "Zone de moyenne densité",
                "IUS_max": 1.0, "COS_max": 0.4,
                "hauteur_corniche_max_m": 13.0, "hauteur_faitage_max_m": 16.0,
                "nb_niveaux_max": 4,
                "stationnement": "1 place / logement + visiteurs 10%",
            },
            "villas": {
                "label": "Zone de villas",
                "IUS_max": 0.45, "COS_max": 0.22,
                "hauteur_corniche_max_m": 7.0, "hauteur_faitage_max_m": 10.0,
                "nb_niveaux_max": 2,
                "stationnement": "2 places / logement",
            },
        },
    },
    "pully": {
        "label": "Pully",
        "reference_reglement": "RCATC Pully",
        "zones": {
            "moyenne_densite": {
                "label": "Zone de moyenne densité",
                "IUS_max": 0.9, "COS_max": 0.35,
                "hauteur_corniche_max_m": 12.0, "hauteur_faitage_max_m": 15.0,
                "nb_niveaux_max": 3,
                "stationnement": "1.2 place / logement",
            },
            "villas": {
                "label": "Zone de villas",
                "IUS_max": 0.4, "COS_max": 0.2,
                "hauteur_corniche_max_m": 7.0, "hauteur_faitage_max_m": 10.0,
                "nb_niveaux_max": 2,
                "stationnement": "2 places / logement",
            },
        },
    },
    "ecublens": {
        "label": "Écublens",
        "reference_reglement": "RPGA Écublens",
        "zones": {
            "habitation_collective": {
                "label": "Zone d'habitation de moyenne densité",
                "IUS_max": 1.1, "COS_max": 0.4,
                "hauteur_corniche_max_m": 13.5, "hauteur_faitage_max_m": 16.5,
                "nb_niveaux_max": 4,
                "stationnement": "1 place / logement (proximité EPFL/UNIL)",
            },
        },
    },
    "morges": {
        "label": "Morges",
        "reference_reglement": "RCATC Morges",
        "zones": {
            "centre_historique": {
                "label": "Zone de la vieille ville",
                "IUS_max": 2.2, "COS_max": 0.75,
                "hauteur_corniche_max_m": 15.0, "hauteur_faitage_max_m": 18.0,
                "nb_niveaux_max": 5,
                "stationnement": "Dérogation centre, report parkings publics",
                "notes": "Périmètre ISOS, préavis patrimoine obligatoire.",
            },
            "moyenne_densite": {
                "label": "Zone de moyenne densité",
                "IUS_max": 1.0, "COS_max": 0.4,
                "hauteur_corniche_max_m": 12.5, "hauteur_faitage_max_m": 15.5,
                "nb_niveaux_max": 4,
                "stationnement": "1 place / logement",
            },
        },
    },
    "nyon": {
        "label": "Nyon",
        "reference_reglement": "RPGA Nyon",
        "zones": {
            "centre": {
                "label": "Zone de centre",
                "IUS_max": 1.8, "COS_max": 0.6,
                "hauteur_corniche_max_m": 16.0, "hauteur_faitage_max_m": 19.0,
                "nb_niveaux_max": 5,
                "stationnement": "0.9 place / logement (gare CFF)",
            },
            "moyenne_densite": {
                "label": "Zone de moyenne densité",
                "IUS_max": 1.0, "COS_max": 0.4,
                "hauteur_corniche_max_m": 12.0, "hauteur_faitage_max_m": 15.0,
                "nb_niveaux_max": 4,
                "stationnement": "1.2 place / logement",
            },
        },
    },
    "yverdon-les-bains": {
        "label": "Yverdon-les-Bains",
        "reference_reglement": "RPGA Yverdon",
        "zones": {
            "centre": {
                "label": "Zone de centre-ville",
                "IUS_max": 2.0, "COS_max": 0.65,
                "hauteur_corniche_max_m": 16.5, "hauteur_faitage_max_m": 20.0,
                "nb_niveaux_max": 5,
                "stationnement": "1 place / logement, réduction centre",
            },
            "moyenne_densite": {
                "label": "Zone d'habitation de moyenne densité",
                "IUS_max": 0.9, "COS_max": 0.4,
                "hauteur_corniche_max_m": 12.0, "hauteur_faitage_max_m": 15.0,
                "nb_niveaux_max": 3,
                "stationnement": "1.2 place / logement",
            },
        },
    },
}


def get_commune_zone(commune: str, zone_key: str) -> dict | None:
    """Retourne les indices d'une zone communale vaudoise précise.

    Args:
        commune: nom commune normalisé (ex: "lausanne", "renens")
        zone_key: identifiant zone communale (ex: "centre_ville", "moyenne_densite")
    """
    commune_data = COMMUNES_VD.get(commune.lower().strip())
    if not commune_data:
        return None
    zone = commune_data["zones"].get(zone_key)
    if not zone:
        return None
    return {
        "commune": commune_data["label"],
        "reglement": commune_data["reference_reglement"],
        "zone_key": zone_key,
        **zone,
    }


def list_communes_vd() -> list[dict]:
    """Liste les communes VD couvertes avec leurs zones."""
    return [
        {
            "commune": key,
            "label": data["label"],
            "reglement": data["reference_reglement"],
            "zones": list(data["zones"].keys()),
        }
        for key, data in COMMUNES_VD.items()
    ]


def check_conformite_commune(
    commune: str,
    zone_key: str,
    surface_terrain_m2: float,
    sbp_projetee_m2: float,
    emprise_sol_m2: float,
    hauteur_corniche_m: float = 0,
    hauteur_faitage_m: float = 0,
    nb_niveaux: int = 0,
) -> dict:
    """Vérifie la conformité d'un projet aux indices communaux VD précis.

    Plus précis que check_conformite_urbanistique() qui utilise les zones
    cantonales génériques.
    """
    zone = get_commune_zone(commune, zone_key)
    if not zone:
        return {"error": f"Zone '{zone_key}' inconnue pour commune '{commune}'. "
                         f"Communes : {[c['commune'] for c in list_communes_vd()]}"}

    ius_projete = sbp_projetee_m2 / surface_terrain_m2 if surface_terrain_m2 else 0
    cos_projete = emprise_sol_m2 / surface_terrain_m2 if surface_terrain_m2 else 0

    depassements = []
    checks = [
        ("IUS_max", ius_projete, zone.get("IUS_max")),
        ("COS_max", cos_projete, zone.get("COS_max")),
        ("hauteur_corniche_max_m", hauteur_corniche_m, zone.get("hauteur_corniche_max_m")),
        ("hauteur_faitage_max_m", hauteur_faitage_m, zone.get("hauteur_faitage_max_m")),
        ("nb_niveaux_max", nb_niveaux, zone.get("nb_niveaux_max")),
    ]
    for regle, valeur, maxi in checks:
        if maxi and valeur and valeur > maxi:
            dep = {"regle": regle, "valeur_max": maxi, "valeur_projetee": round(valeur, 3)}
            if "IUS" in regle or "COS" in regle:
                dep["depassement_pct"] = round((valeur / maxi - 1) * 100, 1)
            depassements.append(dep)

    return {
        "commune": zone["commune"],
        "reglement": zone["reglement"],
        "zone": zone["label"],
        "ius_projete": round(ius_projete, 3),
        "ius_max": zone.get("IUS_max"),
        "cos_projete": round(cos_projete, 3),
        "cos_max": zone.get("COS_max"),
        "stationnement_regle": zone.get("stationnement"),
        "conforme": len(depassements) == 0,
        "depassements": depassements,
        "notes": zone.get("notes"),
        "avertissement": "Indices indicatifs. Valider avec le règlement communal en vigueur.",
    }
