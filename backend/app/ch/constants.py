"""Constantes Suisse romande : cantons, affectations, référentiels SIA/AEAI, stations climatiques SIA 2028."""

# Cantons romands prioritaires + autres CH
CANTONS_ROMANDS = {
    "GE": "Genève",
    "VD": "Vaud",
    "NE": "Neuchâtel",
    "FR": "Fribourg",
    "VS": "Valais",
    "JU": "Jura",
}

CANTONS_AUTRES = {
    "BE": "Berne",
    "ZH": "Zurich",
    "BS": "Bâle-Ville",
    "BL": "Bâle-Campagne",
    "AG": "Argovie",
    "SO": "Soleure",
    "LU": "Lucerne",
    "SG": "Saint-Gall",
    "TI": "Tessin",
    "TG": "Thurgovie",
    "GR": "Grisons",
    "GL": "Glaris",
    "SZ": "Schwytz",
    "OW": "Obwald",
    "NW": "Nidwald",
    "UR": "Uri",
    "ZG": "Zoug",
    "AR": "Appenzell Rhodes-Extérieures",
    "AI": "Appenzell Rhodes-Intérieures",
    "SH": "Schaffhouse",
}

TOUS_CANTONS = {**CANTONS_ROMANDS, **CANTONS_AUTRES}

# Affectations (SIA 380/1)
AFFECTATIONS_SIA = {
    "logement_individuel": "Habitation individuelle",
    "logement_collectif": "Habitation collective",
    "administration": "Administration / bureau",
    "ecole": "École",
    "commerce": "Commerce",
    "restauration": "Restauration",
    "lieu_rassemblement": "Lieu de rassemblement",
    "hopital": "Hôpital",
    "industriel": "Industrie",
    "depot": "Dépôt",
    "sport": "Installation sportive",
    "piscine_couverte": "Piscine couverte",
}

# Phases SIA 102/103/108
PHASES_SIA = {
    "11": "Définition des objectifs",
    "21": "Études préliminaires",
    "31": "Avant-projet",
    "32": "Projet de l'ouvrage",
    "33": "Procédure de demande d'autorisation",
    "41": "Appel d'offres",
    "51": "Projet d'exécution",
    "52": "Exécution de l'ouvrage",
    "53": "Mise en service, achèvement",
    "61": "Exploitation",
    "62": "Maintenance",
}

# TVA Suisse 2024+
VAT_CH = {
    "standard": 8.10,
    "reduit": 2.60,
    "hebergement": 3.80,
    "exempt": 0.0,
}

# Monnaies
CURRENCIES = ["CHF", "EUR"]

# Standards énergétiques suisses
STANDARDS_ENERGETIQUES = {
    "sia_380_1": "SIA 380/1 - Besoins de chaleur",
    "cecb": "CECB - Certificat Énergétique Cantonal des Bâtiments",
    "cecb_plus": "CECB Plus (avec rapport de conseil)",
    "minergie": "MINERGIE",
    "minergie_p": "MINERGIE-P",
    "minergie_a": "MINERGIE-A",
    "minergie_eco": "MINERGIE-ECO",
}

# Zones sismiques SIA 261 (Suisse)
ZONES_SISMIQUES_CH = ["Z1a", "Z1b", "Z2", "Z3a", "Z3b"]

# Classes d'exposition béton SIA 262
CLASSES_EXPOSITION_SIA = {
    "X0": "Aucun risque de corrosion ou d'attaque",
    "XC1": "Sec ou durablement humide",
    "XC2": "Humide, rarement sec",
    "XC3": "Humidité modérée",
    "XC4": "Alternance d'humidité et de sèchement",
    "XD1": "Humidité modérée, chlorures (sauf eau de mer)",
    "XD2": "Humide, rarement sec, chlorures",
    "XD3": "Alternance, chlorures",
    "XS1": "Air marin, sans contact direct",
    "XS2": "Immergé en eau de mer",
    "XS3": "Zones de marnage",
    "XF1": "Saturation modérée sans sel de déverglaçage",
    "XF2": "Saturation modérée avec sel",
    "XF3": "Saturation élevée sans sel",
    "XF4": "Saturation élevée avec sel",
}

# Classes de conséquence SIA 260
CONSEQUENCE_CLASSES = {
    "CC1": "Conséquences faibles",
    "CC2": "Conséquences moyennes",
    "CC3": "Conséquences élevées",
}

# Stations climatiques SIA 2028 (sous-ensemble représentatif - liste complète ~40 stations)
# Données indicatives pour valeurs par défaut
STATIONS_CLIMATIQUES_SIA_2028 = {
    "Genève-Cointrin": {"canton": "GE", "altitude_m": 420, "temp_ext_min_c": -8, "dj_20_12": 3050},
    "Lausanne": {"canton": "VD", "altitude_m": 570, "temp_ext_min_c": -8, "dj_20_12": 3150},
    "Neuchâtel": {"canton": "NE", "altitude_m": 485, "temp_ext_min_c": -10, "dj_20_12": 3280},
    "Fribourg": {"canton": "FR", "altitude_m": 638, "temp_ext_min_c": -12, "dj_20_12": 3550},
    "Sion": {"canton": "VS", "altitude_m": 482, "temp_ext_min_c": -10, "dj_20_12": 3100},
    "La Chaux-de-Fonds": {"canton": "NE", "altitude_m": 1019, "temp_ext_min_c": -15, "dj_20_12": 4250},
    "Payerne": {"canton": "VD", "altitude_m": 490, "temp_ext_min_c": -10, "dj_20_12": 3350},
    "Bulle": {"canton": "FR", "altitude_m": 771, "temp_ext_min_c": -12, "dj_20_12": 3750},
    "Martigny": {"canton": "VS", "altitude_m": 471, "temp_ext_min_c": -8, "dj_20_12": 3050},
    "Montana": {"canton": "VS", "altitude_m": 1508, "temp_ext_min_c": -15, "dj_20_12": 4500},
    "Delémont": {"canton": "JU", "altitude_m": 415, "temp_ext_min_c": -10, "dj_20_12": 3300},
}


def station_default_for_canton(canton: str) -> str:
    """Retourne la station climatique SIA 2028 par défaut pour un canton."""
    defaults = {
        "GE": "Genève-Cointrin",
        "VD": "Lausanne",
        "NE": "Neuchâtel",
        "FR": "Fribourg",
        "VS": "Sion",
        "JU": "Delémont",
    }
    return defaults.get(canton, "Lausanne")


# Typologies AEAI
AEAI_BUILDING_TYPES = {
    "habitation_faible": "Bâtiment d'habitation de faible hauteur (< 11 m)",
    "habitation_moyenne": "Bâtiment d'habitation de moyenne hauteur (11-30 m)",
    "habitation_elevee": "Bâtiment d'habitation élevé (> 30 m)",
    "administration_faible": "Administration / bureau faible hauteur",
    "administration_moyenne": "Administration / bureau moyenne hauteur",
    "administration_elevee": "Administration / bureau hauteur élevée",
    "ecole": "École / enseignement",
    "erp_petit": "Lieu de rassemblement (≤ 300 pers.)",
    "erp_moyen": "Lieu de rassemblement (300-1000 pers.)",
    "erp_grand": "Lieu de rassemblement (> 1000 pers.)",
    "parking_souterrain": "Parking souterrain",
    "industriel": "Bâtiment industriel / artisanal",
    "depot": "Dépôt",
    "hopital": "Hôpital / EMS",
}


# Vecteurs énergétiques pour chauffage (IDC Genève et général)
VECTEURS_ENERGETIQUES = {
    "gaz": {"label": "Gaz naturel", "pci_kwh_par_m3": 10.26, "co2_g_kwh": 228},
    "mazout": {"label": "Mazout", "pci_kwh_par_litre": 9.96, "co2_g_kwh": 301},
    "chauffage_distance": {"label": "Chauffage à distance (CAD)", "co2_g_kwh": 50},
    "pac_air_eau": {"label": "PAC air-eau", "cop_annuel_defaut": 3.0, "co2_g_kwh_elec": 50},
    "pac_sol_eau": {"label": "PAC sol-eau", "cop_annuel_defaut": 4.0, "co2_g_kwh_elec": 50},
    "pellet": {"label": "Pellets / granulés bois", "pci_kwh_par_kg": 4.8, "co2_g_kwh": 30},
    "buche": {"label": "Bûches bois", "pci_kwh_par_m3_stere": 2000, "co2_g_kwh": 30},
    "electrique": {"label": "Électrique direct", "co2_g_kwh": 50},
    "solaire_thermique": {"label": "Solaire thermique", "co2_g_kwh": 20},
}
