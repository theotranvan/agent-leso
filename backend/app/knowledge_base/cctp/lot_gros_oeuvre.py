"""Bibliothèque de clauses types CCTP — Lot GROS ŒUVRE (CFC 211).

Terrassement, béton armé et maçonnerie. Structure CAN (Catalogue des articles
normalisés, CRB) adaptée aux pratiques BET romandes. Contenu rédigé en propre,
normes SIA citées par référence (jamais reproduites).
"""
from __future__ import annotations

# ==========================================================================
# CFC 201 — TERRASSEMENT
# ==========================================================================

CFC_201_TERRASSEMENT = {
    "cfc": "201",
    "intitule": "Terrassement et fouilles",
    "articles": [
        {
            "numero": "201.100",
            "titre": "Fouilles en pleine masse et en rigole",
            "prescriptions": {
                "economique": {
                    "execution": "Décapage terre végétale stockée séparément, fouilles selon plans géomètre",
                    "talutage": "Talus provisoires selon angle de repos du terrain, sans blindage si profondeur < 1.5 m",
                    "evacuation": "Évacuation des déblais en décharge autorisée, tri sur site",
                    "fond_de_fouille": "Réception du fond de fouille par l'ingénieur géotechnicien",
                },
                "standard": {
                    "execution": "Terrassement selon rapport géotechnique SIA 267, fond de fouille dressé et compacté",
                    "talutage": "Blindage des fouilles > 1.5 m (palplanches ou berlinoise) selon étude",
                    "evacuation": "Tri sélectif des matériaux, traçabilité décharge selon OLED, réemploi privilégié",
                    "fond_de_fouille": "Essai de plaque ME ≥ valeur requise, PV de réception géotechnicien",
                    "extras": "Rabattement de nappe si nécessaire selon étude hydrogéologique",
                },
                "premium": {
                    "execution": "Terrassement avec suivi géotechnique permanent, instrumentation des avoisinants",
                    "talutage": "Enceinte de fouille calculée (paroi berlinoise/moulée), monitoring déplacements",
                    "evacuation": "Bilan matières complet OLED, valorisation maximale, sols pollués traités",
                    "fond_de_fouille": "Essais de plaque systématiques par zone, PV individualisés",
                    "extras": "Suivi piézométrique, constat d'huissier des bâtiments voisins",
                },
            },
            "essais_reception": [
                "Réception du fond de fouille par le géotechnicien (PV signé)",
                "Essai de plaque (module ME) sur fond de fouille",
                "Contrôle altimétrique par le géomètre",
            ],
            "normes_referencees": ["SIA 267 (géotechnique)", "SIA 318", "OLED (RS 814.600)"],
            "autorisations": {
                "GE": "Autorisation de fouille / déclaration si rabattement de nappe (GESDEC)",
                "VD": "Annonce DGE si pompage > seuil, gestion des eaux d'épuisement",
            },
        },
    ],
}


# ==========================================================================
# CFC 211 — BÉTON ARMÉ
# ==========================================================================

CFC_211_BETON_ARME = {
    "cfc": "211",
    "intitule": "Béton armé et maçonnerie",
    "articles": [
        {
            "numero": "211.100",
            "titre": "Béton armé pour éléments porteurs",
            "prescriptions": {
                "economique": {
                    "type_beton": "Béton C25/30 selon SN EN 206, classe d'exposition XC2 (intérieur)",
                    "armatures": "Acier B500B selon SIA 262, enrobage selon classe d'exposition",
                    "coffrage": "Coffrage ordinaire, parements non vus, tolérances SIA 414 classe normale",
                    "cure": "Cure du béton 3 jours minimum, protection contre dessiccation",
                },
                "standard": {
                    "type_beton": "Béton C30/37 selon SN EN 206, classes d'exposition XC4/XD1 selon localisation, Dmax 32",
                    "armatures": "Acier B500B, enrobage nominal + tolérance d'exécution selon SIA 262 tableau",
                    "coffrage": "Coffrage soigné parements vus, tolérances SIA 414 classe élevée pour béton apparent",
                    "cure": "Cure soignée 5 jours, plan de bétonnage et reprises validé par l'ingénieur",
                    "extras": "Béton autoplaçant en zones fortement ferraillées, contrôle de l'ouvrabilité",
                },
                "premium": {
                    "type_beton": "Béton C30/37 à C35/45 selon sollicitations, formulation validée, XC4/XD3/XF4 si exposé",
                    "armatures": "Acier B500B avec plan de ferraillage BIM, coupleurs si requis",
                    "coffrage": "Coffrage architectonique parement de classe esthétique définie, échantillon de référence",
                    "cure": "Cure contrôlée (maturométrie), béton à retrait limité en grandes surfaces",
                    "extras": "Béton apparent fibré, joints de reprise étudiés, étanchéité par béton (cuve étanche SIA 272)",
                },
            },
            "essais_reception": [
                "Essais de résistance sur éprouvettes à 28 jours (SN EN 12390)",
                "Contrôle de l'enrobage des armatures (covermètre) avant bétonnage",
                "Réception du ferraillage par l'ingénieur avant coulage",
                "Contrôle de l'ouvrabilité (affaissement / étalement) à la livraison",
            ],
            "normes_referencees": ["SIA 262 (béton)", "SN EN 206", "SIA 414 (tolérances)", "SIA 272 (étanchéité)"],
        },
        {
            "numero": "211.200",
            "titre": "Maçonnerie porteuse et de remplissage",
            "prescriptions": {
                "economique": {
                    "materiau": "Briques en terre cuite ou silico-calcaire selon SIA 266, mortier de montage normalisé",
                    "execution": "Joints pleins, montage à la règle, ancrages selon plans",
                    "tolerances": "Tolérances SIA 414 classe normale",
                },
                "standard": {
                    "materiau": "Briques porteuses SIA 266, résistance selon descente de charges, mortier-colle si requis",
                    "execution": "Chaînages et linteaux béton armé, ancrages inox en façade, joints de dilatation",
                    "tolerances": "Tolérances SIA 414, planéité vérifiée pour support d'enduit",
                    "extras": "Rupteurs de ponts thermiques en pied de mur, première assise étanche",
                },
                "premium": {
                    "materiau": "Briques haute performance (isolantes ou haute résistance), calepinage optimisé",
                    "execution": "Maçonnerie de parement appareillée, joints soignés, échantillon de référence",
                    "tolerances": "Tolérances renforcées pour parement apparent",
                    "extras": "Traitement acoustique des séparatifs SIA 181, désolidarisation des refends",
                },
            },
            "essais_reception": [
                "Contrôle de la planéité et de l'aplomb des murs",
                "Vérification des chaînages et ancrages avant fermeture",
            ],
            "normes_referencees": ["SIA 266 (maçonnerie)", "SIA 414", "SIA 181 (acoustique)"],
        },
    ],
}


# ==========================================================================
# REGISTRE LOT GROS ŒUVRE
# ==========================================================================

LOT_GROS_OEUVRE = {
    "lot_code": "211",
    "lot_intitule": "Gros œuvre — terrassement, béton armé et maçonnerie",
    "cfc_sections": [
        CFC_201_TERRASSEMENT,
        CFC_211_BETON_ARME,
    ],
    "introduction_lot": (
        "Le présent CCTP du lot Gros œuvre (CFC 201/211) décrit les prestations de "
        "terrassement, de béton armé et de maçonnerie. L'ensemble des ouvrages respecte "
        "les normes SIA 260 à 267, la norme béton SN EN 206 et les tolérances SIA 414. "
        "Le dimensionnement structurel découle de la note de calcul statique SIA 260/262 "
        "du projet et du rapport géotechnique."
    ),
    "clauses_generales": [
        "Tous les matériaux sont conformes aux normes suisses (SIA) et européennes (SN EN) en vigueur.",
        "L'entreprise fournit les plans d'exécution, plans de coffrage et de ferraillage validés par l'ingénieur civil avant exécution.",
        "Les classes d'exposition et d'enrobage sont strictement respectées selon le plan de repérage de l'ingénieur.",
        "Toute reprise de bétonnage non prévue fait l'objet d'une validation écrite de l'ingénieur.",
        "Les essais sur éprouvettes et les réceptions de ferraillage sont consignés au dossier d'ouvrage exécuté (DOE).",
    ],
}
