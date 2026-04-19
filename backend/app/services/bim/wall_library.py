"""Bibliothèque de compositions de parois suisses types.

Valeurs indicatives, à valider projet par projet. Utilisées pour pré-remplissage
en phase d'avant-projet.
"""

# Valeurs λ indicatives (W/m·K) - à préciser par fiches produit en phase PRO
MATERIAUX_LAMBDA = {
    "beton_arme": 2.30,
    "beton_armé": 2.30,
    "brique_terre_cuite": 0.45,
    "brique_silico_calcaire": 0.90,
    "plaque_platre": 0.25,
    "bois_tendre": 0.13,
    "bois_massif": 0.13,
    "osb": 0.13,
    "laine_minerale": 0.035,
    "laine_de_verre": 0.035,
    "laine_de_roche": 0.038,
    "polystyrene_expanse": 0.032,
    "polystyrene_extrude": 0.034,
    "polyurethane": 0.024,
    "fibre_bois": 0.040,
    "cellulose": 0.040,
    "liege_expanse": 0.042,
    "enduit_chaux": 0.70,
    "enduit_platre": 0.25,
    "vide_air": 5.88,  # lambda équivalent pour e=2cm
    "parquet": 0.18,
    "carrelage": 1.30,
    "chape_ciment": 1.40,
    "geb_etanch": 0.23,
    "membrane": 0.20,
}

# Résistances superficielles (m²·K/W) selon SIA 180
RSI_EXT = 0.04
RSE_MUR = 0.13
RSE_TOIT = 0.10
RSE_SOL = 0.17


def compute_u_value(layers: list[dict], orientation: str = "vertical") -> float:
    """Calcule le U d'une paroi à partir de ses couches.

    layers = [{material, thickness, lambda_override?}]
    Retourne U en W/m²K.
    """
    r_total = RSI_EXT  # Rsi
    # Rse varie selon orientation
    if orientation == "horizontal_up":
        r_total += RSE_TOIT
    elif orientation == "horizontal_down":
        r_total += RSE_SOL
    else:
        r_total += RSE_MUR

    for layer in layers:
        thickness = layer.get("thickness", 0)
        if thickness <= 0:
            continue
        material = (layer.get("material") or "").lower().replace(" ", "_")
        lam = layer.get("lambda_override") or layer.get("lambda") or MATERIAUX_LAMBDA.get(material, 0)
        if lam <= 0:
            continue
        r_total += thickness / lam

    return round(1.0 / r_total, 3) if r_total > 0 else 0


# Compositions types pour pré-modèle
COMPOSITIONS_TYPES = {
    # Bâtiment neuf performant
    "mur_ext_neuf_perform": {
        "label": "Mur extérieur neuf performant (U ≈ 0.15)",
        "orientation": "vertical",
        "layers": [
            {"material": "plaque_platre", "thickness": 0.015},
            {"material": "laine_minerale", "thickness": 0.040},
            {"material": "beton_arme", "thickness": 0.180},
            {"material": "laine_de_roche", "thickness": 0.200},
            {"material": "enduit_chaux", "thickness": 0.015},
        ],
    },
    "mur_ext_neuf_standard": {
        "label": "Mur extérieur neuf standard (U ≈ 0.20)",
        "orientation": "vertical",
        "layers": [
            {"material": "plaque_platre", "thickness": 0.015},
            {"material": "brique_terre_cuite", "thickness": 0.200},
            {"material": "laine_minerale", "thickness": 0.140},
            {"material": "enduit_chaux", "thickness": 0.015},
        ],
    },
    "mur_ext_renovation": {
        "label": "Mur extérieur rénové (U ≈ 0.25-0.35)",
        "orientation": "vertical",
        "layers": [
            {"material": "plaque_platre", "thickness": 0.015},
            {"material": "beton_arme", "thickness": 0.200},
            {"material": "laine_minerale", "thickness": 0.100},
            {"material": "enduit_chaux", "thickness": 0.015},
        ],
    },
    "toit_neuf_perform": {
        "label": "Toiture neuve performante (U ≈ 0.13)",
        "orientation": "horizontal_up",
        "layers": [
            {"material": "plaque_platre", "thickness": 0.015},
            {"material": "laine_minerale", "thickness": 0.040},
            {"material": "bois_massif", "thickness": 0.050},
            {"material": "laine_minerale", "thickness": 0.300},
            {"material": "osb", "thickness": 0.018},
        ],
    },
    "dalle_sur_terrain_neuf": {
        "label": "Dalle sur terrain neuve (U ≈ 0.22)",
        "orientation": "horizontal_down",
        "layers": [
            {"material": "carrelage", "thickness": 0.010},
            {"material": "chape_ciment", "thickness": 0.080},
            {"material": "polystyrene_extrude", "thickness": 0.140},
            {"material": "beton_arme", "thickness": 0.250},
        ],
    },
    "plancher_inter_etage": {
        "label": "Plancher inter-étage (non thermique direct)",
        "orientation": "horizontal",
        "layers": [
            {"material": "parquet", "thickness": 0.015},
            {"material": "chape_ciment", "thickness": 0.060},
            {"material": "laine_minerale", "thickness": 0.030},
            {"material": "beton_arme", "thickness": 0.220},
        ],
    },
}


def get_composition(key: str) -> dict | None:
    comp = COMPOSITIONS_TYPES.get(key)
    if not comp:
        return None
    u = compute_u_value(comp["layers"], comp.get("orientation", "vertical"))
    return {**comp, "u_value": u, "key": key}


def list_compositions() -> list[dict]:
    return [
        {**get_composition(k), "key": k}
        for k in COMPOSITIONS_TYPES
    ]
