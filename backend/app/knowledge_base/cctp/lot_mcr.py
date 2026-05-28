"""Bibliothèque de clauses types CCTP — Lot MCR (CFC 245 — Mesure, Commande, Régulation)."""

CFC_245_MCR = {
    "cfc": "245",
    "intitule": "Mesure, commande, régulation (MCR / GTB)",
    "articles": [
        {
            "numero": "245.110",
            "titre": "Automate programmable et régulation CVC",
            "prescriptions": {
                "economique": {
                    "automate": "API standard PLC, 64 entrées/sorties minimum",
                    "protocole": "Modbus RTU pour intégration équipements",
                    "interface": "Pupitre tactile 7\" en local technique",
                    "fonctions": "Régulation chauffage pondération extérieure + ECS + ventilation horaire",
                },
                "standard": {
                    "automate": "API modulaire avec extension prévue 20% E/S",
                    "protocole": "BACnet/IP + Modbus pour interopérabilité",
                    "interface": "Pupitre tactile + supervision PC dédiée",
                    "fonctions": "Régulation optimisée + comptages + alarmes + historique 1 an",
                    "extras": "Accès distant sécurisé pour maintenance, gestion utilisateurs",
                },
                "premium": {
                    "automate": "GTC complète avec contrôleurs distribués, redondance",
                    "protocole": "BACnet/IP natif, intégration KNX, OPC UA pour interopérabilité avancée",
                    "interface": "Supervision web HTML5 multi-utilisateur avec droits granulaires",
                    "fonctions": "Optimisation prédictive, scénarios horaires, gestion charges",
                    "extras": "API ouverte pour analytics tiers, tableaux de bord énergétiques",
                },
            },
            "normes_referencees": ["EN ISO 16484", "EN 15232 (classes A à D)"],
        },
        {
            "numero": "245.210",
            "titre": "Sondes et capteurs",
            "prescriptions": {
                "economique": {
                    "temperature": "Sondes Pt1000 classe B selon EN 60751",
                    "humidite": "Sondes capacitives ±5% HR",
                    "pression": "Capteurs piézoélectriques ±2%",
                    "co2": "Sondes NDIR ±50 ppm en grands locaux uniquement",
                },
                "standard": {
                    "temperature": "Sondes Pt1000 classe A, étalonnage SCS si critique",
                    "humidite": "Sondes ±3% HR avec compensation température",
                    "pression": "Capteurs ±1% sur réseaux principaux",
                    "co2": "Sondes NDIR ±30 ppm dans tous locaux occupés en standard",
                    "extras": "Calibration documentée à la mise en service",
                },
                "premium": {
                    "temperature": "Sondes ±0.1°C étalonnées SCS, certificat traçable",
                    "humidite": "Sondes ±2% HR avec compensation et auto-calibration",
                    "pression": "Capteurs haute précision ±0.5% avec affichage local",
                    "co2": "Sondes NDIR doubles canaux ±20 ppm + COV + PM2.5",
                    "extras": "Plan de calibration annuel, traçabilité SCS, monitoring dérive",
                },
            },
            "normes_referencees": ["EN 60751", "EN ISO 16484", "SIA 386.010"],
        },
        {
            "numero": "245.310",
            "titre": "Comptages énergétiques",
            "prescriptions": {
                "economique": {
                    "chaleur": "Compteur chaleur ultrasons MID classe 3",
                    "froid": "Compteur froid MID classe 3 si applicable",
                    "electricite": "Compteurs MID classe 2",
                    "eau": "Compteurs MID R80 minimum",
                },
                "standard": {
                    "chaleur": "Compteur chaleur MID classe 2 par usage (CVS séparés)",
                    "froid": "Compteurs froid MID classe 2 par circuit",
                    "electricite": "Compteurs MID classe 1 sous-comptage par usage (4 minimum)",
                    "eau": "Compteurs MID R160 + sous-comptage ECS",
                    "extras": "Télérelève sur tous les compteurs vers GTC",
                },
                "premium": {
                    "chaleur": "Compteurs MID classe 0.5 + intégrateurs précis, MBus",
                    "froid": "Compteurs MID classe 1 + capteurs débit + delta T",
                    "electricite": "Compteurs MID classe 0.5S + qualité réseau + harmoniques",
                    "eau": "Compteurs MID R250 + détection de fuite intégrée",
                    "extras": "Plan de comptage selon ISO 50001, audit énergétique annuel",
                },
            },
            "normes_referencees": ["OIMes", "EN 1434", "MID 2014/32/UE", "ISO 50001"],
        },
    ],
}

LOT_MCR = {
    "lot_code": "245",
    "lot_intitule": "MCR / GTB",
    "cfc_sections": [CFC_245_MCR],
    "introduction_lot": (
        "Le présent CCTP du lot 245 MCR/GTB décrit la régulation, la supervision et le "
        "comptage des installations techniques. Le niveau de fonctionnalité est conforme à "
        "la classe d'automatisation EN 15232 visée. Les comptages respectent OIMes et MID. "
        "L'architecture permet l'évolution et l'interopérabilité ouverte (BACnet/IP, Modbus)."
    ),
    "clauses_generales": [
        "Le système répond aux exigences de cybersécurité OFCS pour les bâtiments raccordés.",
        "Tous les paramétrages sont documentés (table des points, scénarios, droits utilisateurs).",
        "Une formation à l'exploitant est dispensée à la mise en service.",
        "La GTC est livrée avec une documentation complète et 1 an de garantie évolutive.",
    ],
}
