"""Catalogue initial (seed) des normes et références réglementaires suisses.

IMPORTANT : pour les normes sous licence (SIA, AEAI payantes, NIBT),
on stocke UNIQUEMENT : référence, titre, domaine, millésime, lien source.
On ne reproduit JAMAIS le texte intégral.
"""
from typing import Literal

Domain = Literal["thermique", "structure", "incendie", "electricite",
                 "accessibilite", "acoustique", "general", "documentation"]


# ================================================================
# NORMES FÉDÉRALES SUISSES (publiques, quotable)
# ================================================================
NORMES_FEDERALES = [
    {
        "authority": "Confédération",
        "jurisdiction": ["CH"],
        "reference": "LEne",
        "title": "Loi sur l'énergie (LEne), RS 730.0",
        "domain": ["thermique", "general"],
        "source_url": "https://www.fedlex.admin.ch/eli/cc/2017/762/fr",
        "public_access": True,
        "quotable": True,
        "summary": "Cadre fédéral énergie : politique énergétique, efficacité, promotion des énergies renouvelables.",
    },
    {
        "authority": "Confédération",
        "jurisdiction": ["CH"],
        "reference": "OEne",
        "title": "Ordonnance sur l'énergie (OEne), RS 730.01",
        "domain": ["thermique"],
        "source_url": "https://www.fedlex.admin.ch/eli/cc/2017/763/fr",
        "public_access": True,
        "quotable": True,
        "summary": "Ordonnance d'exécution LEne : exigences, subventions, rapports.",
    },
    {
        "authority": "Confédération",
        "jurisdiction": ["CH"],
        "reference": "LCAP",
        "title": "Loi fédérale sur les constructions adaptées aux personnes handicapées",
        "domain": ["accessibilite"],
        "source_url": "https://www.fedlex.admin.ch/eli/cc/2003/667/fr",
        "public_access": True,
        "quotable": True,
        "summary": "Accessibilité aux bâtiments publics et logements.",
    },
]

# ================================================================
# NORMES CANTONALES ROMANDES (publiques, quotable)
# ================================================================
NORMES_CANTONALES = [
    # GENÈVE
    {
        "authority": "Canton-GE",
        "jurisdiction": ["CH-GE"],
        "reference": "LCI",
        "title": "Loi sur les constructions et installations diverses (GE, L 5 05)",
        "domain": ["general"],
        "source_url": "https://www.ge.ch/legislation/rsg/f/rsg_l5_05.html",
        "public_access": True,
        "quotable": True,
        "summary": "Cadre genevois construction : autorisations, procédures, mises à l'enquête.",
    },
    {
        "authority": "Canton-GE",
        "jurisdiction": ["CH-GE"],
        "reference": "LEn-GE",
        "title": "Loi sur l'énergie (GE, L 2 30)",
        "domain": ["thermique"],
        "source_url": "https://www.ge.ch/legislation/rsg/f/rsg_l2_30.html",
        "public_access": True,
        "quotable": True,
        "summary": "Cadre énergétique cantonal genevois. Inclut régime IDC pour les bâtiments existants.",
    },
    {
        "authority": "Canton-GE",
        "jurisdiction": ["CH-GE"],
        "reference": "REn-GE",
        "title": "Règlement d'application de la loi sur l'énergie (GE, L 2 30.01)",
        "domain": ["thermique"],
        "source_url": "https://www.ge.ch/legislation/rsg/f/rsg_l2_30p01.html",
        "public_access": True,
        "quotable": True,
        "summary": "Dispositions d'application : IDC, exigences bâtiments neufs et rénovation, subventions.",
    },
    {
        "authority": "Canton-GE",
        "jurisdiction": ["CH-GE"],
        "reference": "LDTR",
        "title": "Loi sur les démolitions, transformations et rénovations de maisons d'habitation (GE, L 5 20)",
        "domain": ["general"],
        "source_url": "https://www.ge.ch/legislation/rsg/f/rsg_l5_20.html",
        "public_access": True,
        "quotable": True,
        "summary": "Protection du parc de logements à Genève : autorisations de rénover, loyers.",
    },
    # VAUD
    {
        "authority": "Canton-VD",
        "jurisdiction": ["CH-VD"],
        "reference": "LVLEne",
        "title": "Loi vaudoise sur l'énergie (LVLEne, RSV 730.01)",
        "domain": ["thermique"],
        "source_url": "https://prestations.vd.ch/pub/blv-publication/actes/consolide/730.01",
        "public_access": True,
        "quotable": True,
        "summary": "Cadre énergétique vaudois, intégrant MoPEC. CECB requis pour certaines opérations.",
    },
    {
        "authority": "Canton-VD",
        "jurisdiction": ["CH-VD"],
        "reference": "LATC",
        "title": "Loi sur l'aménagement du territoire et les constructions (VD, RSV 700.11)",
        "domain": ["general"],
        "source_url": "https://prestations.vd.ch/pub/blv-publication/actes/consolide/700.11",
        "public_access": True,
        "quotable": True,
        "summary": "Cadre vaudois construction, permis, procédures.",
    },
    # NEUCHÂTEL
    {
        "authority": "Canton-NE",
        "jurisdiction": ["CH-NE"],
        "reference": "LCEn-NE",
        "title": "Loi cantonale sur l'énergie (Neuchâtel, RSN 740.1)",
        "domain": ["thermique"],
        "source_url": "https://rsn.ne.ch/DATA/program/books/rsne/htm/7401.htm",
        "public_access": True,
        "quotable": True,
        "summary": "Cadre énergétique neuchâtelois.",
    },
    # FRIBOURG
    {
        "authority": "Canton-FR",
        "jurisdiction": ["CH-FR"],
        "reference": "LEn-FR",
        "title": "Loi sur l'énergie (Fribourg, RSF 770.1)",
        "domain": ["thermique"],
        "source_url": "https://bdlf.fr.ch/app/fr/texts_of_law/770.1",
        "public_access": True,
        "quotable": True,
        "summary": "Cadre énergétique fribourgeois.",
    },
    # VALAIS
    {
        "authority": "Canton-VS",
        "jurisdiction": ["CH-VS"],
        "reference": "LcEne-VS",
        "title": "Loi cantonale sur l'énergie (Valais, SGS 730.1)",
        "domain": ["thermique"],
        "source_url": "https://lex.vs.ch/app/fr/texts_of_law/730.1",
        "public_access": True,
        "quotable": True,
        "summary": "Cadre énergétique valaisan.",
    },
]

# ================================================================
# NORMES PRIVÉES / SEMI-PRIVÉES (NON quotable, référencer uniquement)
# ================================================================
NORMES_PRIVEES = [
    # SIA - Société suisse des ingénieurs et architectes
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 380/1:2016",
        "title": "L'énergie thermique dans le bâtiment",
        "domain": ["thermique"],
        "source_url": "https://www.sia.ch/fr/themes/construction-durable/",
        "public_access": False,
        "quotable": False,
        "summary": "Norme centrale suisse pour le calcul des besoins de chaleur. Méthode mensuelle. Valeurs limites par affectation.",
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 180:2014",
        "title": "Protection thermique, protection contre l'humidité et climat intérieur dans les bâtiments",
        "domain": ["thermique"],
        "source_url": "https://www.sia.ch",
        "public_access": False,
        "quotable": False,
        "summary": "Exigences physique du bâtiment : parois, hygrométrie, confort.",
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 2028:2010",
        "title": "Données climatiques pour la physique du bâtiment",
        "domain": ["thermique"],
        "public_access": False,
        "quotable": False,
        "summary": "Stations météo de référence, DJ chauffage, températures extrêmes.",
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 260:2013",
        "title": "Bases pour l'élaboration des projets de structures porteuses",
        "domain": ["structure"],
        "public_access": False,
        "quotable": False,
        "summary": "Bases Eurocode suisses pour ingénierie structurelle.",
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 261:2020",
        "title": "Actions sur les structures porteuses",
        "domain": ["structure"],
        "public_access": False,
        "quotable": False,
        "summary": "Charges permanentes, variables, vent, neige, séisme.",
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 262:2013",
        "title": "Construction en béton",
        "domain": ["structure"],
        "public_access": False,
        "quotable": False,
        "summary": "Dimensionnement béton armé et précontraint.",
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 263:2013",
        "title": "Construction en acier",
        "domain": ["structure"],
        "public_access": False,
        "quotable": False,
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 265:2012",
        "title": "Construction en bois",
        "domain": ["structure"],
        "public_access": False,
        "quotable": False,
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 267:2013",
        "title": "Géotechnique",
        "domain": ["structure"],
        "public_access": False,
        "quotable": False,
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 118:2013",
        "title": "Conditions générales pour l'exécution des travaux de construction",
        "domain": ["documentation"],
        "public_access": False,
        "quotable": False,
        "summary": "Cadre contractuel standard pour marchés de travaux suisses.",
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 451",
        "title": "CAN - Catalogue des articles normalisés (descriptif)",
        "domain": ["documentation"],
        "public_access": False,
        "quotable": False,
        "summary": "Descriptif de soumission normalisé suisse. Équivalent structurel du CCTP français.",
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 500:2009",
        "title": "Constructions sans obstacles",
        "domain": ["accessibilite"],
        "public_access": False,
        "quotable": False,
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 181:2020",
        "title": "Protection contre le bruit dans le bâtiment",
        "domain": ["acoustique"],
        "public_access": False,
        "quotable": False,
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 102:2020",
        "title": "Règlement concernant les prestations et honoraires des architectes",
        "domain": ["documentation"],
        "public_access": False,
        "quotable": False,
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 103:2020",
        "title": "Règlement concernant les prestations et honoraires des ingénieurs civils",
        "domain": ["documentation"],
        "public_access": False,
        "quotable": False,
    },
    {
        "authority": "SIA",
        "jurisdiction": ["CH"],
        "reference": "SIA 108:2020",
        "title": "Règlement concernant les prestations et honoraires des ingénieurs dans les domaines de l'ingénierie mécanique et électrique",
        "domain": ["documentation"],
        "public_access": False,
        "quotable": False,
    },
    # AEAI - Association des établissements cantonaux d'assurance incendie
    {
        "authority": "AEAI",
        "jurisdiction": ["CH"],
        "reference": "AEAI 1-15f",
        "title": "Norme de protection incendie (édition 2015)",
        "domain": ["incendie"],
        "source_url": "https://www.praever.ch/fr/bs/vs",
        "public_access": False,
        "quotable": False,
        "summary": "Norme de base de la protection incendie applicable en Suisse.",
    },
    {
        "authority": "AEAI",
        "jurisdiction": ["CH"],
        "reference": "AEAI 10-15f",
        "title": "Directive de protection incendie : termes et définitions",
        "domain": ["incendie"],
        "public_access": False,
        "quotable": False,
    },
    {
        "authority": "AEAI",
        "jurisdiction": ["CH"],
        "reference": "AEAI 15-15f",
        "title": "Directive : Distances de sécurité incendie, systèmes porteurs et compartimentage",
        "domain": ["incendie"],
        "public_access": False,
        "quotable": False,
    },
    # Electrosuisse
    {
        "authority": "Electrosuisse",
        "jurisdiction": ["CH"],
        "reference": "NIBT 2020",
        "title": "Norme sur les installations à basse tension (SNR 462638/NIBT)",
        "domain": ["electricite"],
        "source_url": "https://www.electrosuisse.ch",
        "public_access": False,
        "quotable": False,
        "summary": "Équivalent suisse de la NF C 15-100. Obligatoire pour les installations BT.",
    },
    # MINERGIE
    {
        "authority": "MINERGIE",
        "jurisdiction": ["CH"],
        "reference": "MINERGIE 2023",
        "title": "Standard MINERGIE",
        "domain": ["thermique"],
        "source_url": "https://www.minergie.ch",
        "public_access": True,  # principes publics
        "quotable": True,
    },
]


def all_seed_norms() -> list[dict]:
    """Retourne la liste complète des normes à insérer initialement."""
    return NORMES_FEDERALES + NORMES_CANTONALES + NORMES_PRIVEES


# ================================================================
# IDC Genève - informations clés
# ================================================================
# Note : ces valeurs sont indicatives et doivent être validées avec OCEN Genève
# avant usage opérationnel. Source : LEn-GE / REn-GE (consultation requise)
IDC_GE_CONFIG = {
    "unite": "MJ/m²/an",
    "seuils_indicatifs": {
        "logement": {
            "cible": 450,          # indicatif
            "elevé": 600,          # déclenche plan d'assainissement
            "tres_eleve": 800,     # action obligatoire rapide
        },
        "administration": {
            "cible": 400,
            "eleve": 550,
        },
    },
    "periode_chauffage_type": {"start_month": 10, "end_month": 4},
    "note": "Valeurs indicatives — toujours vérifier la LEn/REn-GE en vigueur",
}
