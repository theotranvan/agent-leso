"""Bibliothèque de clauses types CCTP — Lot CHAUFFAGE (CFC 230).

Structure CAN (Catalogue des articles normalisés) suisse :
  - Référence CFC à 3 chiffres (230 = chauffage, 231 = production chaleur, etc.)
  - Article CAN avec numéro
  - Texte prescriptif normalisé (sans reproduction des normes SIA, mais avec référence)
  - Niveau de prestation : économique / standard / premium

Source méthodologique : structure inspirée du Catalogue des articles normalisés (CRB),
adaptée aux pratiques BET romandes. Le contenu est rédigé en propre, jamais copié.
"""
from __future__ import annotations

from typing import Literal

NiveauPrestation = Literal["economique", "standard", "premium"]


# ==========================================================================
# CFC 231 — PRODUCTION DE CHALEUR
# ==========================================================================

CFC_231_PRODUCTION_CHALEUR = {
    "cfc": "231",
    "intitule": "Production de chaleur",
    "articles": [
        {
            "numero": "231.110",
            "titre": "Pompe à chaleur air-eau",
            "prescriptions": {
                "economique": {
                    "puissance_nominale": "Selon dimensionnement SIA 384/3, point bivalent à -7°C",
                    "cop_min_a7w35": "COP ≥ 4.0 à A7/W35 selon EN 14511",
                    "scop_min": "SCOP ≥ 3.8 zone climatique B selon EN 14825",
                    "niveau_sonore": "≤ 55 dB(A) à 5 m",
                    "regulation": "Régulation à pondération extérieure intégrée",
                    "certification": "Label HP Keymark requis",
                    "garantie": "Garantie constructeur 2 ans, compresseur 5 ans",
                },
                "standard": {
                    "puissance_nominale": "Selon dimensionnement SIA 384/3 avec coefficient de simultanéité",
                    "cop_min_a7w35": "COP ≥ 4.5 à A7/W35 selon EN 14511",
                    "scop_min": "SCOP ≥ 4.2 zone climatique B selon EN 14825",
                    "niveau_sonore": "≤ 50 dB(A) à 5 m, mode nuit ≤ 45 dB(A)",
                    "regulation": "Régulation pondération extérieure + sonde ambiance, communication Modbus",
                    "certification": "Label HP Keymark + Minergie-Modul si requis",
                    "garantie": "Garantie 5 ans pièces et main-d'œuvre, compresseur 10 ans",
                    "fluide_frigorigene": "R32 ou R290 (GWP < 700)",
                },
                "premium": {
                    "puissance_nominale": "Dimensionnement SIA 384/3 avec étude bivalente, valeur nominale et appoint",
                    "cop_min_a7w35": "COP ≥ 5.0 à A7/W35 selon EN 14511",
                    "scop_min": "SCOP ≥ 4.8 zone climatique B selon EN 14825",
                    "niveau_sonore": "≤ 45 dB(A) à 5 m, mode silence ≤ 40 dB(A)",
                    "regulation": "Régulation prédictive avec apprentissage, GTC KNX/Modbus/BACnet",
                    "certification": "Label HP Keymark + Minergie-Modul + EHPA Q-Label",
                    "garantie": "Garantie 10 ans pièces, main-d'œuvre 5 ans, compresseur 10 ans",
                    "fluide_frigorigene": "R290 (propane, GWP = 3)",
                    "extras": "Compteur de chaleur intégré, monitoring distant via cloud sécurisé CH",
                },
            },
            "essais_reception": [
                "Mesure de COP en conditions normalisées (A7/W35)",
                "Mesure du niveau sonore selon EN 12102",
                "Vérification de la régulation et des sondes",
                "Mise en service par installateur certifié constructeur",
                "Procès-verbal de mise en service signé (template OFEN 2024)",
            ],
            "normes_referencees": ["SIA 384/3", "EN 14511", "EN 14825", "EN 12102"],
        },
        {
            "numero": "231.120",
            "titre": "Pompe à chaleur géothermique (sondes verticales)",
            "prescriptions": {
                "economique": {
                    "puissance_nominale": "Selon SIA 384/6, longueur de sonde justifiée par dimensionnement EED",
                    "cop_min_b0w35": "COP ≥ 4.3 à B0/W35 selon EN 14511",
                    "scop_min": "SCOP ≥ 4.5 selon EN 14825",
                    "sondes": "Sondes PE-Xa double-U DN32, profondeur selon EED",
                    "fluide_caloporteur": "Mélange eau/glycol 25% éthylène, non toxique",
                    "regulation": "Régulation pondération extérieure",
                },
                "standard": {
                    "puissance_nominale": "SIA 384/6 avec simulation EED 4.20, vérification SPF ≥ 4.0",
                    "cop_min_b0w35": "COP ≥ 4.8 à B0/W35 selon EN 14511",
                    "scop_min": "SCOP ≥ 5.0 selon EN 14825",
                    "sondes": "Sondes PE-Xa double-U DN32 ou DN40, autorisation cantonale (GE: GESDEC, VD: DGE)",
                    "fluide_caloporteur": "Mélange eau/propylène-glycol 25%, biodégradable",
                    "regulation": "Régulation pondération + sonde ambiance, monitoring SPF",
                    "extras": "Test de réponse thermique (TRT) si surface > 1500 m²",
                },
                "premium": {
                    "puissance_nominale": "SIA 384/6 + simulation dynamique EED, validation par tiers",
                    "cop_min_b0w35": "COP ≥ 5.5 à B0/W35 selon EN 14511",
                    "scop_min": "SCOP ≥ 5.5 selon EN 14825",
                    "sondes": "Sondes coaxiales haute performance, TRT obligatoire",
                    "fluide_caloporteur": "Eau pure si profondeur permet, sinon propylène-glycol 20%",
                    "regulation": "GTC complète avec optimisation prédictive, free-cooling été",
                    "extras": "Compteurs de chaleur sondes individuels, mesure SPF continue",
                },
            },
            "essais_reception": [
                "Test d'étanchéité des sondes (pression 6 bar, 1h)",
                "Mesure du COP en conditions de test",
                "Vérification du débit de la boucle géothermique",
                "Test de réponse thermique si applicable (TRT)",
                "Mise en service avec relevé initial des compteurs",
            ],
            "normes_referencees": ["SIA 384/6", "SIA 384/7", "EN 14511", "Norme SIA 384/6:2021"],
            "autorisations": {
                "GE": "Concession DGS pour sondes > 100 m, déclaration GESDEC obligatoire",
                "VD": "Permis DGE/DIREV, étude hydrogéologique selon zone",
                "FR": "Autorisation SEn Fribourg, carte des zones favorables",
            },
        },
        {
            "numero": "231.210",
            "titre": "Chaudière à pellets",
            "prescriptions": {
                "economique": {
                    "puissance_nominale": "Selon SIA 384/2, modulation 30-100%",
                    "rendement_min": "Rendement saisonnier ≥ 85% selon EN 303-5",
                    "classe_emissions": "Classe 5 selon EN 303-5",
                    "stockage_silo": "Silo textile 1.5 t minimum, autonomie 2 semaines",
                    "regulation": "Régulation à pondération extérieure",
                },
                "standard": {
                    "puissance_nominale": "SIA 384/2 avec ballon tampon dimensionné selon EN 303-5 (min 20 L/kW)",
                    "rendement_min": "Rendement saisonnier ≥ 92% selon EN 303-5",
                    "classe_emissions": "Classe 5 + label Q de l'Association suisse pour l'énergie du bois",
                    "stockage_silo": "Silo maçonné ou textile, autonomie 4 semaines minimum",
                    "regulation": "Régulation Lambda + sonde ambiance + commande à distance",
                    "extras": "Aspiration auto pellets, décendrage automatique",
                },
                "premium": {
                    "puissance_nominale": "Cascade de chaudières pour modulation 10-100% complète",
                    "rendement_min": "Rendement saisonnier ≥ 95% selon EN 303-5",
                    "classe_emissions": "Classe 5 + Label Énergie-bois Suisse Plus",
                    "stockage_silo": "Silo maçonné dédié, autonomie saisonnière",
                    "regulation": "GTC complète avec optimisation, monitoring émissions",
                    "extras": "Filtre à particules électrostatique, condensation des fumées",
                },
            },
            "essais_reception": [
                "Mesure des émissions (CO, NOx, particules) selon OPair",
                "Vérification du rendement de combustion",
                "Test du système d'évacuation des fumées (tirage)",
                "Mise en service avec ramonage technique initial",
            ],
            "normes_referencees": ["SIA 384/2", "EN 303-5", "OPair (RS 814.318.142.1)"],
        },
        {
            "numero": "231.310",
            "titre": "Raccordement chauffage à distance (CAD)",
            "prescriptions": {
                "economique": {
                    "puissance_souscrite": "Selon calcul de charge SIA 384/2",
                    "sous_station": "Sous-station à plaques avec compteur de chaleur classe 2",
                    "temperatures": "Primaire selon contrat distributeur, secondaire 50/30°C",
                    "regulation": "Régulation pondération extérieure secondaire",
                },
                "standard": {
                    "puissance_souscrite": "Calcul SIA 384/2 + foisonnement, marge 15%",
                    "sous_station": "Sous-station à plaques, compteur classe 1, télérelève",
                    "temperatures": "Primaire selon contrat, secondaire 45/30°C pour plancher chauffant",
                    "regulation": "Régulation pondération + sonde ambiance, communication Modbus",
                    "extras": "Compteurs individuels par appartement (LDTR-GE si applicable)",
                },
                "premium": {
                    "puissance_souscrite": "Calcul fin avec simulation thermique dynamique du bâtiment",
                    "sous_station": "Sous-station haute performance, compteurs MID classe 1",
                    "temperatures": "Optimisation basse température 40/30°C ou moins",
                    "regulation": "GTC complète, prédiction de charge, intégration GED bâtiment",
                    "extras": "Stockage tampon pour effacement de pointe, monitoring distant",
                },
            },
            "essais_reception": [
                "Test de pression et étanchéité sous-station",
                "Vérification compteur (étalonnage MID)",
                "Mise en service contradictoire avec distributeur",
                "Procès-verbal SIG/SIL/SiG selon distributeur",
            ],
            "normes_referencees": ["SIA 384/2", "OIMes (RS 941.210)", "OFE 2024 télérelève"],
        },
    ],
}


# ==========================================================================
# CFC 232 — DISTRIBUTION DE CHALEUR
# ==========================================================================

CFC_232_DISTRIBUTION = {
    "cfc": "232",
    "intitule": "Distribution de chaleur",
    "articles": [
        {
            "numero": "232.110",
            "titre": "Tuyauterie acier noir soudé",
            "prescriptions": {
                "economique": {
                    "materiau": "Acier noir EN 10220, soudage TIG ou MAG",
                    "isolation": "Coquilles laine minérale 30 mm, jaquette PVC",
                    "supports": "Colliers galvanisés, écartement selon SIA 384/2",
                    "essai_pression": "1.5 × pression service, durée 2 h",
                },
                "standard": {
                    "materiau": "Acier noir EN 10220 soudé TIG, raccords à bride DN ≥ 50",
                    "isolation": "Coquilles laine de roche λ ≤ 0.040 W/mK, épaisseur SIA 380/1 tableau 13",
                    "supports": "Colliers anti-vibration, points fixes calculés",
                    "essai_pression": "1.5 × pression service, durée 4 h avec attestation",
                    "extras": "Purgeurs automatiques en points hauts, vannes d'équilibrage",
                },
                "premium": {
                    "materiau": "Acier noir EN 10220 soudé TIG avec radiographie sur 10% des soudures",
                    "isolation": "Coquilles laine de roche + jaquette aluminium en zones techniques",
                    "supports": "Supports anti-vibratoires + compensateurs dilatation calculés",
                    "essai_pression": "Test hydraulique + test à l'air comprimé 6 bar 24 h",
                    "extras": "Capteurs de fuite, vannes d'isolement par zone, équilibrage hydraulique tracé",
                },
            },
            "normes_referencees": ["SIA 384/2", "EN 10220", "SIA 380/1 tableau 13"],
        },
        {
            "numero": "232.210",
            "titre": "Plancher chauffant basse température",
            "prescriptions": {
                "economique": {
                    "tuyaux": "PE-Xa 16/2, conforme EN ISO 15875",
                    "pas_de_pose": "10 cm en zones de bord, 15-20 cm en zones courantes",
                    "chape": "Chape ciment min 65 mm sur tuyaux, conforme SIA 251",
                    "regulation": "Collecteur avec débitmètres, sonde ambiance par pièce",
                    "temperature": "Régime 35/28°C, limitation 27°C surface",
                },
                "standard": {
                    "tuyaux": "PE-Xa avec barrière anti-oxygène EVOH, 17/2 mm",
                    "pas_de_pose": "Calcul individualisé par pièce selon charges thermiques",
                    "chape": "Chape ciment auto-nivelante 65 mm + plot de désolidarisation",
                    "regulation": "Régulation pièce par pièce, vannes thermostatiques motorisées",
                    "temperature": "Régime 35/28°C optimisé pour PAC",
                    "extras": "Bandes de bord périphériques, plaques de répartition aluminium",
                },
                "premium": {
                    "tuyaux": "PE-Xa multicouche avec EVOH, certification SVGW",
                    "pas_de_pose": "Calcul thermique par pièce avec simulation dynamique",
                    "chape": "Chape anhydrite haute conductivité λ ≥ 1.6 W/mK, plots résiliants",
                    "regulation": "Régulation digitale par pièce, sondes sol + ambiance, intégration GTB",
                    "temperature": "Régime ultra basse température 32/27°C pour PAC géothermique",
                    "extras": "Test thermographique avant chape, plan d'exécution coté détaillé",
                },
            },
            "essais_reception": [
                "Essai de pression 6 bar pendant 24 h avant chape",
                "Test thermographique IR avant et après mise en service",
                "Procès-verbal de mise en service et d'équilibrage",
                "Plan d'exécution AS-BUILT avec position des sondes",
            ],
            "normes_referencees": ["SIA 384/2", "SIA 251", "EN 1264", "EN ISO 15875"],
        },
    ],
}


# ==========================================================================
# CFC 233 — ÉMISSION DE CHALEUR
# ==========================================================================

CFC_233_EMISSION = {
    "cfc": "233",
    "intitule": "Émission de chaleur",
    "articles": [
        {
            "numero": "233.110",
            "titre": "Radiateurs panneaux acier",
            "prescriptions": {
                "economique": {
                    "type": "Radiateurs panneaux acier laqué, EN 442",
                    "dimensionnement": "Selon SIA 384/2, régime 70/55°C",
                    "vannes": "Vannes thermostatiques tête liquide, certifiées EN 215",
                    "fixation": "Consoles murales standards",
                },
                "standard": {
                    "type": "Radiateurs panneaux double avec ailettes, raccordement central",
                    "dimensionnement": "SIA 384/2 régime 55/40°C, calcul par pièce",
                    "vannes": "Vannes thermostatiques électroniques programmables EN 215",
                    "fixation": "Consoles renforcées, étanchéité parement",
                    "extras": "Bouchons assortis, peinture cuite ral au choix architecte",
                },
                "premium": {
                    "type": "Radiateurs design (sèche-serviettes, verticaux décoratifs)",
                    "dimensionnement": "Dimensionnement précis régime 50/35°C, marge 0% (juste)",
                    "vannes": "Vannes thermostatiques digitales communicantes (Z-Wave ou KNX)",
                    "fixation": "Consoles dissimulées, raccordement plinthe ou sol",
                    "extras": "Robinetterie laiton chromé, purgeur micrométrique",
                },
            },
            "normes_referencees": ["SIA 384/2", "EN 442", "EN 215"],
        },
    ],
}


# ==========================================================================
# REGISTRE LOT CHAUFFAGE
# ==========================================================================

LOT_CHAUFFAGE = {
    "lot_code": "230",
    "lot_intitule": "Chauffage",
    "cfc_sections": [
        CFC_231_PRODUCTION_CHALEUR,
        CFC_232_DISTRIBUTION,
        CFC_233_EMISSION,
    ],
    "introduction_lot": (
        "Le présent CCTP du lot 230 Chauffage décrit les prestations relatives à la "
        "production, la distribution et l'émission de chaleur. L'ensemble des prestations "
        "respecte les normes SIA 384/1, SIA 384/2 et les exigences cantonales applicables. "
        "Le dimensionnement est conforme au programme énergétique défini en phase d'avant-projet "
        "et au justificatif SIA 380/1 du projet."
    ),
    "clauses_generales": [
        "Tous les matériaux et équipements sont conformes aux normes suisses et européennes en vigueur.",
        "L'entreprise présente un dossier d'exécution avec plans, schémas et fiches techniques avant tout début de travaux.",
        "Toutes les modifications par rapport au CCTP doivent faire l'objet d'une variante écrite, signée par le maître d'ouvrage et le BET.",
        "Le coordinateur sécurité-santé doit être informé de toute intervention en hauteur ou en espace confiné.",
        "La mise en service est conditionnée à la remise des procès-verbaux d'essais et du dossier d'ouvrage exécuté (DOE).",
    ],
}
