"""Bibliothèque de clauses types CCTP — Lot ÉLECTRICITÉ (CFC 230 partiel + 240)."""

CFC_240_ELECTRICITE = {
    "cfc": "240",
    "intitule": "Installations électriques",
    "articles": [
        {
            "numero": "241.110",
            "titre": "Tableau général basse tension (TGBT)",
            "prescriptions": {
                "economique": {
                    "calibre": "Selon calcul charge SIA 380 + NIBT, marge ≥ 20%",
                    "construction": "Armoire métallique IP30 intérieur, IP54 extérieur",
                    "appareillage": "Disjoncteurs modulaires NIBT 2020, courbe C",
                    "protection_dr": "DDR 30 mA type AC sur circuits prises et SDB",
                    "comptage": "Compteur principal MID classe 2",
                },
                "standard": {
                    "calibre": "Calcul SIA 380 avec étude harmoniques si onduleurs",
                    "construction": "Armoire modulaire avec compartimentage par fonction",
                    "appareillage": "Disjoncteurs NIBT 2020 + parafoudre T2",
                    "protection_dr": "DDR 30 mA type A sur tous circuits prises et SDB, type B sur recharge VE",
                    "comptage": "Compteur intelligent (smart meter) MID classe 1",
                    "extras": "Sous-comptage par usage (chauffage, éclairage, prises)",
                },
                "premium": {
                    "calibre": "Étude qualité réseau complète, dimensionnement avec scénarios",
                    "construction": "Armoire IP54 avec sectionnement et compartimentage IEC 61439",
                    "appareillage": "Disjoncteurs débrochables, parafoudres T1+T2+T3, surveillance distance",
                    "protection_dr": "DDR sélectifs 300/100/30 mA + monitoring courant de fuite continu",
                    "comptage": "Compteurs MID classe 0.5S communicants, monitoring qualité réseau",
                    "extras": "Onduleur central pour circuits critiques, télégestion via GTC",
                },
            },
            "essais_reception": [
                "Test diélectrique 1500 V pendant 1 minute",
                "Mesure de continuité du conducteur PE",
                "Mesure d'isolement > 500 MΩ",
                "Test fonctionnel des DDR avec courant de défaut calibré",
                "Procès-verbal de mise en service signé électricien autorisé OIBT",
                "Rapport de sécurité OIBT à la mise en service",
            ],
            "normes_referencees": ["NIBT 2020", "OIBT", "SN EN 61439", "SIA 380"],
        },
        {
            "numero": "242.110",
            "titre": "Câblage et distribution",
            "prescriptions": {
                "economique": {
                    "cables_alimentation": "Câbles cuivre type T (TT 1.0/1.5/2.5/4 mm² selon charges)",
                    "cheminements": "Tubes plastiques en encastré, chemins de câbles en local technique",
                    "sectionnement": "Coupure générale par étage",
                    "section_minimale": "1.5 mm² éclairage, 2.5 mm² prises 16A, 4 mm² circuits cuisine",
                },
                "standard": {
                    "cables_alimentation": "Câbles halogen-free LSZH en sortie tableau et zones publiques",
                    "cheminements": "Chemins de câbles galvanisés, tubes ICTA encastrés",
                    "sectionnement": "Sectionnement par zone et par usage",
                    "section_minimale": "Selon NIBT avec coefficient de simultanéité par usage",
                    "extras": "Câblage avec marquage permanent, plan de repérage",
                },
                "premium": {
                    "cables_alimentation": "Tous câbles halogen-free LSZH, résistance feu CR1 sur dorsales",
                    "cheminements": "Chemins de câbles inox en locaux humides, séparation courants forts/faibles",
                    "sectionnement": "Sectionnement par zone EN/CEM, surveillance continuité",
                    "section_minimale": "Calcul individualisé par circuit avec marge de réserve 30%",
                    "extras": "Système de cassettes de sol pour bureaux flex, attestation EMC",
                },
            },
            "normes_referencees": ["NIBT 2020 chapitre 4.4", "EN 50575"],
        },
        {
            "numero": "243.110",
            "titre": "Éclairage intérieur LED",
            "prescriptions": {
                "economique": {
                    "luminaires": "LED IRC ≥ 80, classe énergétique A++",
                    "eclairement": "Selon SIA 380/4, 300 lux bureaux, 100 lux circulations",
                    "regulation": "Interrupteurs manuels, détection présence en circulations",
                    "garantie": "5 ans pièces",
                },
                "standard": {
                    "luminaires": "LED IRC ≥ 90, MacAdam ≤ 3 SDCM, UGR ≤ 19 bureaux",
                    "eclairement": "SIA 380/4 + uniformité ≥ 0.6, calcul DIALux par local",
                    "regulation": "Détection présence + variation 1-10V, scènes pré-programmées",
                    "garantie": "5 ans pièces + main-d'œuvre",
                    "extras": "Gradation par DALI dans bureaux, circuit lumière naturelle",
                },
                "premium": {
                    "luminaires": "LED IRC ≥ 95, MacAdam ≤ 2 SDCM, certificat photobiologique",
                    "eclairement": "Calcul DIALux + simulation visuelle, confort SIA 180",
                    "regulation": "DALI-2 avec capteurs lumière du jour, GTC complète",
                    "garantie": "10 ans pièces + main-d'œuvre",
                    "extras": "Human Centric Lighting (variation température couleur), monitoring qualité",
                },
            },
            "normes_referencees": ["SIA 380/4", "EN 12464-1", "SIA 180"],
        },
        {
            "numero": "246.110",
            "titre": "Prises pour véhicules électriques",
            "prescriptions": {
                "economique": {
                    "borne": "Mode 3 Type 2, 7.4 kW (32A monophasé)",
                    "compteur": "Compteur dédié MID",
                    "protection": "DDR type B 30 mA dédié",
                    "infrastructure": "Pré-câblage pour 30% des places (article 226 LCAP)",
                },
                "standard": {
                    "borne": "Mode 3 Type 2, 11 kW triphasé (16A)",
                    "compteur": "Compteur communicant avec gestion charge",
                    "protection": "DDR type B + parafoudre",
                    "infrastructure": "Pré-câblage 100% places + 50% bornes installées",
                    "extras": "Pilotage de charge dynamique (load management)",
                },
                "premium": {
                    "borne": "Mode 3 Type 2, 22 kW + 1 borne rapide CCS si besoin",
                    "compteur": "Comptage MID + facturation via plateforme cloud (e-mobility)",
                    "protection": "DDR type B + monitoring isolement continu",
                    "infrastructure": "100% bornes installées + couverture PV dédiée",
                    "extras": "V2G ready, intégration GTC bâtiment, réservation par app",
                },
            },
            "normes_referencees": ["IEC 61851-1", "EN 17186", "NIBT 2020 chapitre 7.22"],
        },
        {
            "numero": "247.110",
            "titre": "Détection incendie",
            "prescriptions": {
                "economique": {
                    "type": "Détecteurs optiques de fumée selon AEAI",
                    "centrale": "Centrale conventionnelle adressable selon classification",
                    "alarme": "Sirènes intérieures, asservissement portes coupe-feu",
                    "certification": "Installateur certifié AEAI",
                },
                "standard": {
                    "type": "Détecteurs multicritères (fumée + chaleur)",
                    "centrale": "Centrale adressable EN 54 avec transmission télécom",
                    "alarme": "Sirènes intérieures + flashs, transmission centre télésurveillance",
                    "certification": "Installateur certifié AEAI, contrôles annuels obligatoires",
                    "extras": "Plan d'évacuation intégré, désenfumage asservi",
                },
                "premium": {
                    "type": "Détecteurs adressables haute sensibilité + détection aspirante en locaux critiques",
                    "centrale": "Système redondant EN 54, double alimentation, dialogue GTC",
                    "alarme": "Sonorisation évacuation EN 54-16 + sirènes + flashs + signalétique dynamique",
                    "certification": "AEAI + maintenance prédictive avec rapports automatisés",
                    "extras": "Intégration avec contrôle d'accès et CCTV, désenfumage à pilotage scénarisé",
                },
            },
            "normes_referencees": ["AEAI 17-15f", "EN 54", "AEAI 26-15f sonorisation"],
        },
    ],
}

LOT_ELECTRICITE = {
    "lot_code": "240",
    "lot_intitule": "Électricité",
    "cfc_sections": [CFC_240_ELECTRICITE],
    "introduction_lot": (
        "Le présent CCTP du lot 240 Électricité couvre l'ensemble des installations électriques "
        "courants forts et courants faibles : tableau général, distribution, éclairage, prises "
        "VE, détection incendie. Toutes les installations respectent la NIBT 2020, l'OIBT et "
        "les directives AEAI pour la détection incendie. Les exigences SIA 380/4 sont appliquées "
        "pour l'éclairage."
    ),
    "clauses_generales": [
        "L'installateur dispose d'une autorisation OIBT pour les travaux exécutés.",
        "Un rapport de sécurité OIBT est remis au maître d'ouvrage à la mise en service.",
        "Tous les câbles en cheminement collectif sont halogen-free LSZH minimum.",
        "Les schémas électriques AS-BUILT sont remis au format DXF/DWG + PDF.",
        "Les essais NIBT sont consignés dans un procès-verbal signé par l'installateur autorisé.",
    ],
}
