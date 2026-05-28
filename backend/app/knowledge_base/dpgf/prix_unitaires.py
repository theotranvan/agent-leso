"""Base de prix unitaires DPGF — Suisse romande (CHF HT, indice 2025).

Source méthodologique : prix de marché construction Suisse romande basés sur :
  - Indices KBOB (Conférence de coordination des services de la construction)
  - Statistiques CRB (Centre suisse d'études pour la rationalisation de la construction)
  - Retours BET romands moyens 2024-2025
  - Indice ZH/BS/GE ajustés région Vaud/Genève

Fourchettes données en min/median/max — l'agent retient la médiane par défaut
et ajuste selon le niveau de prestation et la complexité du projet.

ATTENTION : prix indicatifs à valider en consultation. Variations possibles ±15%
selon entreprise, conjoncture, accessibilité chantier, volume.
"""
from __future__ import annotations


# ==========================================================================
# LOT CHAUFFAGE (CFC 230) — prix moyens CHF HT
# ==========================================================================

PRIX_CHAUFFAGE = {
    "231.110": {  # Pompe à chaleur air-eau
        "designation": "PAC air-eau, mise en place et raccordement, sans sondes",
        "unite": "kW thermique installé",
        "prix": {
            "economique": {"min": 1100, "median": 1350, "max": 1600},
            "standard": {"min": 1400, "median": 1700, "max": 2000},
            "premium": {"min": 1900, "median": 2300, "max": 2800},
        },
        "notes": "Hors travaux de gros-œuvre. Plage typique 6-30 kW résidentiel.",
    },
    "231.120": {  # PAC géothermique sondes
        "designation": "PAC géothermique avec sondes verticales (forage inclus)",
        "unite": "kW thermique installé",
        "prix": {
            "economique": {"min": 2500, "median": 2900, "max": 3300},
            "standard": {"min": 3100, "median": 3600, "max": 4100},
            "premium": {"min": 3900, "median": 4500, "max": 5200},
        },
        "notes": "Forage 25-50 CHF/ml + sondes + PAC. Compter ~25 ml/kW en zone B.",
    },
    "231.210": {  # Chaudière pellets
        "designation": "Chaudière à pellets avec silo, hors maçonnerie",
        "unite": "kW thermique installé",
        "prix": {
            "economique": {"min": 900, "median": 1100, "max": 1300},
            "standard": {"min": 1200, "median": 1500, "max": 1800},
            "premium": {"min": 1800, "median": 2200, "max": 2600},
        },
        "notes": "Hors silo maçonné. Compter +5000-15000 CHF pour silo selon taille.",
    },
    "231.310": {  # Sous-station CAD
        "designation": "Sous-station chauffage à distance, échangeur à plaques",
        "unite": "kW puissance souscrite",
        "prix": {
            "economique": {"min": 350, "median": 450, "max": 550},
            "standard": {"min": 500, "median": 650, "max": 800},
            "premium": {"min": 750, "median": 950, "max": 1200},
        },
        "notes": "Hors taxe de raccordement réseau (forfait variable selon distributeur).",
    },
    "232.110": {  # Tuyauterie acier
        "designation": "Tuyauterie acier noir soudée isolée, pose chemin de câbles",
        "unite": "ml posé",
        "prix": {
            "economique": {"min": 75, "median": 95, "max": 115},
            "standard": {"min": 100, "median": 130, "max": 160},
            "premium": {"min": 140, "median": 180, "max": 220},
        },
        "notes": "Diamètre moyen DN32-DN50. Prix au ml majoré sur DN65+.",
    },
    "232.210": {  # Plancher chauffant
        "designation": "Plancher chauffant complet (tuyauterie, plaques, collecteur, mise en eau)",
        "unite": "m² au sol",
        "prix": {
            "economique": {"min": 75, "median": 90, "max": 105},
            "standard": {"min": 95, "median": 115, "max": 135},
            "premium": {"min": 130, "median": 160, "max": 195},
        },
        "notes": "Hors chape. Chape ciment +35-45 CHF/m².",
    },
    "233.110": {  # Radiateurs
        "designation": "Radiateur panneaux acier avec vanne thermostatique, pose",
        "unite": "kW d'émission",
        "prix": {
            "economique": {"min": 250, "median": 320, "max": 400},
            "standard": {"min": 380, "median": 480, "max": 580},
            "premium": {"min": 650, "median": 850, "max": 1100},
        },
        "notes": "Prix dépend du design. Sèche-serviettes design >1100 CHF/kW.",
    },
}

# ==========================================================================
# LOT VENTILATION (CFC 244)
# ==========================================================================

PRIX_VENTILATION = {
    "244.110": {  # Centrale double flux
        "designation": "CTA double flux avec récupérateur, motorisée EC",
        "unite": "m³/h débit nominal",
        "prix": {
            "economique": {"min": 4.50, "median": 5.50, "max": 6.50},
            "standard": {"min": 6.00, "median": 7.50, "max": 9.00},
            "premium": {"min": 8.50, "median": 11.00, "max": 13.50},
        },
        "notes": "Hors gaines et bouches. Plage typique 500-5000 m³/h.",
    },
    "244.210": {  # Gaines galvanisées
        "designation": "Gaines galvanisées isolées, pose chemin",
        "unite": "ml posé (équivalent DN200)",
        "prix": {
            "economique": {"min": 85, "median": 105, "max": 125},
            "standard": {"min": 110, "median": 140, "max": 170},
            "premium": {"min": 160, "median": 200, "max": 250},
        },
        "notes": "Coefficient de complexité +20% pour gaines rectangulaires.",
    },
    "244.120": {  # VMC simple flux hygro
        "designation": "VMC simple flux hygroréglable (caisson + bouches + réseau)",
        "unite": "logement équivalent",
        "prix": {
            "economique": {"min": 1400, "median": 1750, "max": 2100},
            "standard": {"min": 1900, "median": 2400, "max": 2900},
            "premium": {"min": 2700, "median": 3400, "max": 4200},
        },
        "notes": "Par logement type 3.5 pièces. Hors gaines verticales collectives.",
    },
    "244.410": {  # Rafraîchissement
        "designation": "Rafraîchissement de confort (batterie froide ou plafond rafraîchissant)",
        "unite": "m² rafraîchi",
        "prix": {
            "economique": {"min": 25, "median": 35, "max": 50},
            "standard": {"min": 60, "median": 85, "max": 120},
            "premium": {"min": 130, "median": 180, "max": 250},
        },
        "notes": "Free-cooling seul = économique. Plafonds rafraîchissants = premium.",
    },
    "244.310": {  # Bouches/diffuseurs
        "designation": "Bouche ou diffuseur, fourniture et pose",
        "unite": "pièce",
        "prix": {
            "economique": {"min": 80, "median": 110, "max": 140},
            "standard": {"min": 130, "median": 175, "max": 220},
            "premium": {"min": 250, "median": 350, "max": 500},
        },
        "notes": "Diffuseur design ou induction haute performance >500 CHF.",
    },
}

# ==========================================================================
# LOT SANITAIRE (CFC 250)
# ==========================================================================

PRIX_SANITAIRE = {
    "251.110": {  # Production ECS
        "designation": "Ballon ECS avec préparateur, isolation, raccordements",
        "unite": "L volume ballon",
        "prix": {
            "economique": {"min": 4.50, "median": 5.50, "max": 6.50},
            "standard": {"min": 6.00, "median": 7.50, "max": 9.00},
            "premium": {"min": 9.50, "median": 12.50, "max": 16.00},
        },
        "notes": "Plage typique 300-2000L. PAC ECS dédiée +5000-8000 CHF en sus.",
    },
    "252.110_ef": {  # Distribution EF
        "designation": "Distribution eau froide, tubes PE-Xa, raccords",
        "unite": "ml posé (équivalent DN25)",
        "prix": {
            "economique": {"min": 35, "median": 45, "max": 55},
            "standard": {"min": 50, "median": 65, "max": 80},
            "premium": {"min": 75, "median": 100, "max": 130},
        },
    },
    "252.110_ec": {  # Distribution ECS
        "designation": "Distribution ECS isolée, tubes PE-Xa, raccords sertis",
        "unite": "ml posé (équivalent DN25)",
        "prix": {
            "economique": {"min": 55, "median": 70, "max": 85},
            "standard": {"min": 75, "median": 95, "max": 115},
            "premium": {"min": 110, "median": 140, "max": 180},
        },
    },
    "253.110": {  # Évacuations
        "designation": "Évacuations PE-HD, colonnes et collecteurs",
        "unite": "ml posé (équivalent DN110)",
        "prix": {
            "economique": {"min": 65, "median": 80, "max": 95},
            "standard": {"min": 85, "median": 110, "max": 135},
            "premium": {"min": 130, "median": 170, "max": 220},
        },
        "notes": "Fonte ductile insonorisée +50% prix.",
    },
    "254.110_wc": {
        "designation": "WC complet (cuvette, réservoir encastré, plaque de commande)",
        "unite": "pièce",
        "prix": {
            "economique": {"min": 650, "median": 850, "max": 1050},
            "standard": {"min": 950, "median": 1250, "max": 1550},
            "premium": {"min": 1500, "median": 2200, "max": 3500},
        },
    },
    "254.110_lavabo": {
        "designation": "Lavabo complet avec robinetterie",
        "unite": "pièce",
        "prix": {
            "economique": {"min": 450, "median": 600, "max": 800},
            "standard": {"min": 750, "median": 1000, "max": 1300},
            "premium": {"min": 1200, "median": 1800, "max": 3000},
        },
    },
    "254.110_douche": {
        "designation": "Douche complète (receveur, robinetterie, paroi)",
        "unite": "pièce",
        "prix": {
            "economique": {"min": 950, "median": 1200, "max": 1500},
            "standard": {"min": 1400, "median": 1800, "max": 2200},
            "premium": {"min": 2200, "median": 3000, "max": 4500},
        },
    },
}

# ==========================================================================
# LOT ÉLECTRICITÉ (CFC 240)
# ==========================================================================

PRIX_ELECTRICITE = {
    "241.110_tgbt": {  # Tableau général
        "designation": "Tableau général BT, calibre selon charge, armoire complète",
        "unite": "A intensité nominale",
        "prix": {
            "economique": {"min": 18, "median": 22, "max": 26},
            "standard": {"min": 24, "median": 30, "max": 36},
            "premium": {"min": 35, "median": 45, "max": 58},
        },
        "notes": "Plage typique 40-630A. Tableaux modulaires IEC 61439.",
    },
    "241.110_secondaire": {
        "designation": "Tableau divisionnaire d'étage ou de zone",
        "unite": "pièce (équipée jusqu'à 24 modules)",
        "prix": {
            "economique": {"min": 850, "median": 1100, "max": 1350},
            "standard": {"min": 1200, "median": 1550, "max": 1900},
            "premium": {"min": 1800, "median": 2400, "max": 3200},
        },
    },
    "242.110": {  # Câblage
        "designation": "Câblage courants forts, pose chemin et tirage",
        "unite": "m² SRE",
        "prix": {
            "economique": {"min": 35, "median": 45, "max": 55},
            "standard": {"min": 50, "median": 65, "max": 80},
            "premium": {"min": 75, "median": 95, "max": 120},
        },
        "notes": "Inclut tirage, pose chemins, raccordement. Hors luminaires.",
    },
    "243.110": {  # Luminaires LED
        "designation": "Luminaire LED encastré ou apparent, pose",
        "unite": "pièce (équivalent 30W)",
        "prix": {
            "economique": {"min": 95, "median": 130, "max": 165},
            "standard": {"min": 150, "median": 200, "max": 250},
            "premium": {"min": 280, "median": 400, "max": 600},
        },
        "notes": "Luminaires design ou Human Centric Lighting >600 CHF/pce.",
    },
    "245.110_prise_simple": {
        "designation": "Prise 230V T13, fourniture et pose",
        "unite": "pièce",
        "prix": {
            "economique": {"min": 65, "median": 85, "max": 105},
            "standard": {"min": 85, "median": 115, "max": 145},
            "premium": {"min": 130, "median": 175, "max": 230},
        },
    },
    "246.110_ve": {
        "designation": "Borne de recharge VE 11 kW Type 2",
        "unite": "pièce",
        "prix": {
            "economique": {"min": 2200, "median": 2800, "max": 3500},
            "standard": {"min": 3000, "median": 3800, "max": 4600},
            "premium": {"min": 4500, "median": 5800, "max": 7500},
        },
        "notes": "Hors infrastructure câblage et compteur. Précâblage +500-1000 CHF par place.",
    },
    "247.110_detection_incendie": {
        "designation": "Détection incendie complète (centrale + détecteurs + sirènes)",
        "unite": "m² SRE",
        "prix": {
            "economique": {"min": 18, "median": 23, "max": 28},
            "standard": {"min": 25, "median": 32, "max": 40},
            "premium": {"min": 38, "median": 50, "max": 65},
        },
        "notes": "Pour bâtiments > 1000 m². Coefficient -20% sur petites surfaces.",
    },
}

# ==========================================================================
# LOT MCR (CFC 245)
# ==========================================================================

PRIX_MCR = {
    "245.110_gtb": {
        "designation": "GTB / GTC complète, automate + supervision",
        "unite": "m² SRE",
        "prix": {
            "economique": {"min": 18, "median": 22, "max": 28},
            "standard": {"min": 25, "median": 32, "max": 40},
            "premium": {"min": 40, "median": 55, "max": 75},
        },
        "notes": "Inclut automate, sondes, vannes 3 voies, supervision, mise en service.",
    },
    "245.310_compteur_chaleur": {
        "designation": "Compteur de chaleur ultrasons MID classe 2, DN20-DN40",
        "unite": "pièce",
        "prix": {
            "economique": {"min": 650, "median": 850, "max": 1050},
            "standard": {"min": 950, "median": 1200, "max": 1500},
            "premium": {"min": 1400, "median": 1800, "max": 2300},
        },
    },
    "245.310_smart_meter": {
        "designation": "Compteur électrique communicant MID classe 1",
        "unite": "pièce",
        "prix": {
            "economique": {"min": 280, "median": 360, "max": 440},
            "standard": {"min": 400, "median": 520, "max": 640},
            "premium": {"min": 620, "median": 800, "max": 1000},
        },
    },
}


# ==========================================================================
# REGISTRE CONSOLIDÉ
# ==========================================================================

PRIX_DPGF_REGISTRY = {
    "230": PRIX_CHAUFFAGE, "chauffage": PRIX_CHAUFFAGE, "cvs": PRIX_CHAUFFAGE,
    "244": PRIX_VENTILATION, "ventilation": PRIX_VENTILATION,
    "250": PRIX_SANITAIRE, "sanitaire": PRIX_SANITAIRE,
    "240": PRIX_ELECTRICITE, "electricite": PRIX_ELECTRICITE,
    "245": PRIX_MCR, "mcr": PRIX_MCR, "gtb": PRIX_MCR,
}


# ==========================================================================
# COEFFICIENTS RÉGIONAUX (par rapport à indice Suisse romande = 1.00)
# ==========================================================================

COEFFICIENTS_REGIONAUX = {
    "GE": 1.08,   # Genève premium
    "VD": 1.00,   # Vaud référence
    "NE": 0.94,   # Neuchâtel
    "FR": 0.96,   # Fribourg
    "VS": 0.92,   # Valais
    "JU": 0.90,   # Jura
    "ZH": 1.05,   # Zurich pour info
    "BS": 1.02,   # Bâle pour info
}


# ==========================================================================
# API SIMPLIFIÉE
# ==========================================================================

def get_prix_unitaire(
    lot_key: str,
    article_code: str,
    niveau: str = "standard",
    canton: str = "VD",
) -> dict | None:
    """Retourne le prix unitaire ajusté pour un article et un canton.

    Returns:
        {designation, unite, prix_min, prix_median, prix_max, canton, coefficient}
    """
    lot_prix = PRIX_DPGF_REGISTRY.get(lot_key.lower())
    if not lot_prix:
        return None

    article = lot_prix.get(article_code)
    if not article:
        return None

    prix_niveau = article["prix"].get(niveau, article["prix"]["standard"])
    coef = COEFFICIENTS_REGIONAUX.get(canton.upper(), 1.0)

    return {
        "designation": article["designation"],
        "unite": article["unite"],
        "prix_min": round(prix_niveau["min"] * coef, 2),
        "prix_median": round(prix_niveau["median"] * coef, 2),
        "prix_max": round(prix_niveau["max"] * coef, 2),
        "niveau": niveau,
        "canton": canton.upper(),
        "coefficient_regional": coef,
        "notes": article.get("notes"),
    }


def list_prix_for_lot(lot_key: str, niveau: str = "standard", canton: str = "VD") -> list[dict]:
    """Retourne tous les prix d'un lot, ajustés au canton et au niveau."""
    lot_prix = PRIX_DPGF_REGISTRY.get(lot_key.lower())
    if not lot_prix:
        return []

    coef = COEFFICIENTS_REGIONAUX.get(canton.upper(), 1.0)
    out = []
    for code, article in lot_prix.items():
        prix_niveau = article["prix"].get(niveau, article["prix"]["standard"])
        out.append({
            "code": code,
            "designation": article["designation"],
            "unite": article["unite"],
            "prix_min": round(prix_niveau["min"] * coef, 2),
            "prix_median": round(prix_niveau["median"] * coef, 2),
            "prix_max": round(prix_niveau["max"] * coef, 2),
            "notes": article.get("notes"),
        })
    return out


def estimate_lot_cost(
    lot_key: str,
    quantites: dict[str, float],  # {article_code: quantite}
    niveau: str = "standard",
    canton: str = "VD",
) -> dict:
    """Estime le coût total d'un lot à partir de quantités par article.

    Args:
        lot_key: "chauffage", "ventilation"...
        quantites: dict mapping article_code → quantité (selon unité de l'article)
        niveau: economique / standard / premium
        canton: code canton

    Returns:
        Dict avec total min/median/max et détail par poste.
    """
    detail = []
    total_min = total_med = total_max = 0.0

    for code, qte in quantites.items():
        prix = get_prix_unitaire(lot_key, code, niveau, canton)
        if not prix:
            detail.append({"code": code, "qte": qte, "erreur": "prix introuvable"})
            continue
        ligne = {
            "code": code,
            "designation": prix["designation"],
            "unite": prix["unite"],
            "quantite": qte,
            "prix_unitaire_min": prix["prix_min"],
            "prix_unitaire_median": prix["prix_median"],
            "prix_unitaire_max": prix["prix_max"],
            "total_min": round(qte * prix["prix_min"], 2),
            "total_median": round(qte * prix["prix_median"], 2),
            "total_max": round(qte * prix["prix_max"], 2),
        }
        detail.append(ligne)
        total_min += ligne["total_min"]
        total_med += ligne["total_median"]
        total_max += ligne["total_max"]

    return {
        "lot": lot_key,
        "niveau": niveau,
        "canton": canton.upper(),
        "total_min_chf": round(total_min, 2),
        "total_median_chf": round(total_med, 2),
        "total_max_chf": round(total_max, 2),
        "detail": detail,
        "note": "Prix indicatifs HT, à valider en consultation. Indice 2025.",
    }
