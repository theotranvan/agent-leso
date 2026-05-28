"""Bibliothèque de clauses types CCTP — Lot VENTILATION (CFC 244)."""
from __future__ import annotations


CFC_244_VENTILATION = {
    "cfc": "244",
    "intitule": "Installations de ventilation et climatisation",
    "articles": [
        {
            "numero": "244.110",
            "titre": "Ventilation double flux avec récupération de chaleur",
            "prescriptions": {
                "economique": {
                    "debit_dimensionnement": "Selon SIA 382/1 et SIA 2024, 30 m³/h/pers en bureaux",
                    "rendement_recuperateur": "≥ 75% selon EN 308",
                    "filtration": "F7 sur air neuf, G4 sur air repris",
                    "ventilateurs": "EC à variation de vitesse, SFP ≤ 1.0 kW/(m³/s)",
                    "regulation": "Régulation horaire avec sondes CO2 en grands locaux",
                    "isolation_acoustique": "Pièges à son intégrés, niveau ≤ 35 dB(A) dans locaux",
                },
                "standard": {
                    "debit_dimensionnement": "SIA 382/1 avec calcul détaillé par local, foisonnement",
                    "rendement_recuperateur": "≥ 85% selon EN 308, échangeur à plaques contre-courant",
                    "filtration": "F7 air neuf + ePM1 50% (anciennement F7), G4 reprise",
                    "ventilateurs": "EC à commutation électronique, SFP ≤ 0.8 kW/(m³/s)",
                    "regulation": "Sondes CO2 + VOC + humidité, débit variable VAV",
                    "isolation_acoustique": "Niveau ≤ 30 dB(A) en chambres, ≤ 35 dB(A) en bureaux",
                    "extras": "Bypass d'été automatique, free-cooling nocturne",
                },
                "premium": {
                    "debit_dimensionnement": "Simulation CFD pour locaux complexes, qualité d'air SIA 382/2",
                    "rendement_recuperateur": "≥ 90% échangeur rotatif enthalpique avec récupération humidité",
                    "filtration": "ePM1 80% + filtration moléculaire (charbon actif) si pollution",
                    "ventilateurs": "Moteurs EC haute efficacité IE5, SFP ≤ 0.6 kW/(m³/s)",
                    "regulation": "Sondes CO2/COV/PM2.5/humidité + GTC complète + apprentissage prédictif",
                    "isolation_acoustique": "Niveau ≤ 25 dB(A) salles silencieuses, mesure NR/NC",
                    "extras": "Récupération chaleur sur eaux grises, monitoring qualité air en temps réel",
                },
            },
            "essais_reception": [
                "Mesure des débits par local selon NF EN 12599 ou SICC 2024-1",
                "Mesure du rendement échangeur selon EN 308",
                "Mesure du niveau sonore en service",
                "Mesure du SFP des ventilateurs",
                "Test d'étanchéité des gaines selon EN 12237 classe C minimum",
                "Procès-verbal d'équilibrage aéraulique",
            ],
            "normes_referencees": ["SIA 382/1", "SIA 382/2", "SIA 2024", "EN 308", "EN 12599", "SICC 2024-1"],
        },
        {
            "numero": "244.210",
            "titre": "Réseau de gaines galvanisées",
            "prescriptions": {
                "economique": {
                    "materiau": "Tôle galvanisée Z275 selon EN 10346",
                    "etancheite": "Classe B selon EN 12237",
                    "isolation": "Laine minérale 30 mm sur gaines en zone non chauffée",
                    "fixation": "Suspensions par tige filetée, écartement selon DIN 4140",
                },
                "standard": {
                    "materiau": "Tôle galvanisée Z275 ou inox 304 en cuisine/sanitaires",
                    "etancheite": "Classe C selon EN 12237",
                    "isolation": "Laine minérale 50 mm + jaquette aluminium",
                    "fixation": "Suspensions anti-vibratoires en sortie de ventilateurs",
                    "extras": "Trappes de visite tous les 6 m et à chaque changement de direction",
                },
                "premium": {
                    "materiau": "Inox 304 ou 316 pour cuisines collectives et hottes",
                    "etancheite": "Classe D selon EN 12237, test obligatoire",
                    "isolation": "Laine minérale 80 mm + jaquette alu, pare-vapeur en zone humide",
                    "fixation": "Suspensions élastomère + compensateurs souples",
                    "extras": "Endoscopie de toutes les gaines en réception, plan AS-BUILT",
                },
            },
            "normes_referencees": ["EN 10346", "EN 12237", "DIN 4140", "SIA 382/1"],
        },
        {
            "numero": "244.120",
            "titre": "Ventilation mécanique contrôlée simple flux hygroréglable",
            "prescriptions": {
                "economique": {
                    "principe": "Extraction hygroréglable type B, entrées d'air autoréglables en façade",
                    "debit_dimensionnement": "Selon SIA 382/1, débits modulés par taux d'humidité",
                    "ventilateurs": "Caisson d'extraction basse consommation, SFP ≤ 0.4 kW/(m³/s)",
                    "regulation": "Bouches hygroréglables sans énergie",
                    "acoustique": "Pièges à son sur réseau collectif, ≤ 30 dB(A) en logement",
                },
                "standard": {
                    "principe": "VMC hygro B avec détection présence dans sanitaires",
                    "debit_dimensionnement": "SIA 382/1 avec calcul par typologie de logement",
                    "ventilateurs": "Caisson EC à débit constant régulé, SFP ≤ 0.35 kW/(m³/s)",
                    "regulation": "Bouches hygroréglables + temporisation cuisine/SDB",
                    "acoustique": "≤ 28 dB(A) en pièces de vie",
                    "extras": "Caisson en toiture avec rejet maîtrisé, trappe de visite",
                },
                "premium": {
                    "principe": "VMC hygro B haut de gamme ou bascule double flux selon saison",
                    "debit_dimensionnement": "Calcul individualisé, étanchéité réseau classe C",
                    "ventilateurs": "Caisson EC ultra-silencieux, SFP ≤ 0.25 kW/(m³/s)",
                    "regulation": "Sondes humidité + CO2 dans pièces principales",
                    "acoustique": "≤ 25 dB(A), mesure NR en réception",
                    "extras": "Monitoring débits et alarme encrassement filtre",
                },
            },
            "essais_reception": [
                "Mesure des débits extraits par bouche selon SICC 2024-1",
                "Mesure acoustique en logement type",
                "Vérification du fonctionnement hygroréglable",
            ],
            "normes_referencees": ["SIA 382/1", "SIA 2024", "SICC 2024-1", "SIA 181"],
        },
        {
            "numero": "244.410",
            "titre": "Rafraîchissement / climatisation de confort",
            "prescriptions": {
                "economique": {
                    "principe": "Free-cooling nocturne par sur-ventilation, pas de groupe froid",
                    "dimensionnement": "Selon SIA 382/1 charges thermiques d'été, limitation surchauffe SIA 180",
                    "regulation": "Pilotage horaire bypass récupérateur",
                    "objectif_confort": "T° intérieure ≤ 26.5°C (catégorie III SIA 180)",
                },
                "standard": {
                    "principe": "Rafraîchissement adiabatique ou batterie froide sur CTA",
                    "dimensionnement": "Calcul charges + simulation thermique dynamique simplifiée",
                    "regulation": "Régulation T° de soufflage + sondes ambiance",
                    "objectif_confort": "T° ≤ 26°C (catégorie II SIA 180), free-cooling prioritaire",
                    "extras": "Récupération sur PAC réversible si présente",
                },
                "premium": {
                    "principe": "Plafonds rafraîchissants ou poutres climatiques + free-cooling géothermique",
                    "dimensionnement": "Simulation thermique dynamique complète (IDA-ICE ou équivalent)",
                    "regulation": "GTC avec optimisation prédictive et anti-condensation",
                    "objectif_confort": "T° ≤ 25.5°C (catégorie I SIA 180), confort élevé",
                    "extras": "Géocooling sur sondes géothermiques, COP froid > 15",
                },
            },
            "essais_reception": [
                "Mesure du confort thermique d'été selon SIA 180 (PMV/PPD)",
                "Vérification absence de condensation sur émetteurs froids",
                "Mesure puissance frigorifique et COP",
            ],
            "normes_referencees": ["SIA 382/1", "SIA 180", "SIA 382/2"],
        },
        {
            "numero": "244.310",
            "titre": "Bouches et diffuseurs",
            "prescriptions": {
                "economique": {
                    "soufflage": "Diffuseurs à fentes ou plafonniers, vitesse résiduelle ≤ 0.20 m/s",
                    "reprise": "Grilles à ailettes fixes, réglage débit par registre",
                    "finition": "Laquage RAL au choix architecte",
                },
                "standard": {
                    "soufflage": "Diffuseurs à induction réglables, vitesse résiduelle ≤ 0.18 m/s",
                    "reprise": "Grilles à ailettes orientables, registres équilibrage",
                    "finition": "Laquage thermolaquage + cadre dissimulé",
                    "extras": "Filtres F7 démontables sur reprises en zones sensibles",
                },
                "premium": {
                    "soufflage": "Diffuseurs design intégrés (plafond, déplacement), confort SIA 180",
                    "reprise": "Grilles haute induction avec filtration intégrée",
                    "finition": "Sur mesure architecte, intégration plafond acoustique",
                    "extras": "Test confort SIA 180 (vitesse air, DR < 15%, PMV/PPD)",
                },
            },
            "normes_referencees": ["SIA 180", "SIA 382/1", "EN 13182"],
        },
    ],
}

LOT_VENTILATION = {
    "lot_code": "244",
    "lot_intitule": "Ventilation",
    "cfc_sections": [CFC_244_VENTILATION],
    "introduction_lot": (
        "Le présent CCTP du lot 244 Ventilation décrit les installations de ventilation "
        "mécanique double flux avec récupération de chaleur, le réseau de distribution "
        "et les éléments terminaux. Les prestations respectent les normes SIA 382/1, "
        "SIA 382/2, SIA 2024 et les exigences sanitaires SIA 180. La conception privilégie "
        "le confort intérieur et l'efficacité énergétique conformément au standard énergétique "
        "défini pour le projet."
    ),
    "clauses_generales": [
        "Les débits sont conformes à SIA 382/1 et SIA 2024 selon l'affectation des locaux.",
        "L'entreprise fournit le plan d'équilibrage aéraulique et procède à la mesure contradictoire.",
        "Les filtres sont remplacés avant la mise en service finale (test de classification).",
        "Le nettoyage des gaines est documenté avant mise en service (endoscopie en option premium).",
    ],
}
