"""Bibliothèque de clauses types CCTP — Lot SANITAIRE (CFC 250)."""

CFC_250_SANITAIRE = {
    "cfc": "250",
    "intitule": "Installations sanitaires",
    "articles": [
        {
            "numero": "251.110",
            "titre": "Production d'eau chaude sanitaire (ECS)",
            "prescriptions": {
                "economique": {
                    "production": "Préparateur ECS avec serpentin, isolation classe B",
                    "volume_ballon": "Selon SIA 385/1, 25 L/personne/jour",
                    "temperature": "60°C en ballon, 55°C en circulation",
                    "anti_legionellose": "Choc thermique 70°C hebdomadaire",
                    "energie": "Couverture solaire ≥ 30% selon LEne",
                },
                "standard": {
                    "production": "Ballon ECS avec échangeur externe, isolation classe A",
                    "volume_ballon": "SIA 385/1 + simulation profil consommation",
                    "temperature": "55°C en ballon avec mitigeur thermostatique 50°C sortie",
                    "anti_legionellose": "Boucle de retour permanente + désinfection thermique programmée",
                    "energie": "PAC ECS dédiée ou solaire thermique 40-60% couverture",
                    "extras": "Compteurs ECS individuels (LDTR si applicable)",
                },
                "premium": {
                    "production": "PAC dédiée + ballon stratifié + appoint solaire",
                    "volume_ballon": "Simulation dynamique avec courbe de charge mesurée",
                    "temperature": "Stratification 60°C haut / 30°C bas, mitigeurs individuels",
                    "anti_legionellose": "Désinfection UV ou monitoring continu",
                    "energie": "Solaire thermique 60%+ ou PAC double service géothermique",
                    "extras": "Récupération chaleur eaux grises, monitoring consommation par appartement",
                },
            },
            "essais_reception": [
                "Test d'étanchéité réseau ECS (10 bar pendant 24 h)",
                "Mesure des températures en différents points",
                "Vérification du débit de la boucle de retour",
                "Analyse bactériologique (légionelles) avant mise en service",
                "Procès-verbal de mise en service avec relevés initiaux",
            ],
            "normes_referencees": ["SIA 385/1", "SIA 385/2", "SVGW W3", "OPair"],
        },
        {
            "numero": "252.110",
            "titre": "Distribution eau froide et eau chaude",
            "prescriptions": {
                "economique": {
                    "materiau_ef": "Tubes PE-Xa avec barrière oxygène, conforme SVGW W3/E1",
                    "materiau_ec": "PE-Xa résistant 70°C continu, 95°C ponctuel",
                    "isolation": "Coquilles 9 mm minimum, conformes SIA 385/1",
                    "robinetterie": "Vannes à boisseau sphérique laiton chromé",
                },
                "standard": {
                    "materiau_ef": "PE-Xa multicouche aluminium, SVGW certifié",
                    "materiau_ec": "PE-Xa multicouche, raccords sertis",
                    "isolation": "Coquilles ≥ 13 mm, jaquette en zone visible",
                    "robinetterie": "Vannes laiton, points de vidange à chaque colonne",
                    "extras": "Compteurs individuels MID classe 2",
                },
                "premium": {
                    "materiau_ef": "PE-Xa multicouche inox compatible Eau-Suisse",
                    "materiau_ec": "Inox 316L pour réseaux principaux, PE-Xa terminal",
                    "isolation": "Coquilles 19 mm + jaquette aluminium intégrale",
                    "robinetterie": "Robinetterie certifiée KIWA Gold ou équivalent",
                    "extras": "Détection de fuite par capteurs, compteurs communicants",
                },
            },
            "normes_referencees": ["SVGW W3", "SVGW W3/E1", "SIA 385/1"],
        },
        {
            "numero": "253.110",
            "titre": "Évacuations eaux usées et pluviales",
            "prescriptions": {
                "economique": {
                    "materiau_eu": "PE/PP haute densité, soudures à miroir",
                    "materiau_ep": "PE ou PVC selon DGE/SIG cantonal",
                    "dimensionnement": "Selon SIA 190 et règlements communaux",
                    "ventilation": "Colonnes ventilées en toiture",
                },
                "standard": {
                    "materiau_eu": "PE-HD soudé, isolation phonique en gaine",
                    "materiau_ep": "PE-HD avec rétention en toiture si requis",
                    "dimensionnement": "Calcul individuel par tronçon SIA 190",
                    "ventilation": "Aérateurs primaires et secondaires",
                    "extras": "Acoustique SIA 181 respectée, séparation gravitaire/relevage",
                },
                "premium": {
                    "materiau_eu": "Fonte ductile insonorisée en colonnes verticales",
                    "materiau_ep": "Toitures végétalisées avec rétention dimensionnée",
                    "dimensionnement": "Modélisation hydraulique avec scénarios pluie centennale",
                    "ventilation": "Système Sovent ou équivalent pour grands collectifs",
                    "extras": "Récupération eaux pluviales pour usage WC/arrosage",
                },
            },
            "normes_referencees": ["SIA 190", "SIA 181", "VSA", "norme cantonale"],
        },
        {
            "numero": "254.110",
            "titre": "Appareils sanitaires",
            "prescriptions": {
                "economique": {
                    "wc": "WC suspendu avec réservoir encastré, double touche 3/6 L",
                    "lavabo": "Lavabo céramique avec mitigeur monocommande classe débit Z",
                    "douche": "Receveur acrylique + paroi + mitigeur thermostatique",
                    "robinetterie": "Mitigeurs économes classe A (≤ 6 L/min lavabo)",
                    "accessibilite": "1 sanitaire adapté PMR par niveau public (SIA 500)",
                },
                "standard": {
                    "wc": "WC suspendu sans bride, réservoir encastré Geberit/Laufen, plaque inox",
                    "lavabo": "Lavabo céramique qualité + mitigeur à limiteur de débit et température",
                    "douche": "Receveur extra-plat + paroi verre sécurit + barre thermostatique",
                    "robinetterie": "Robinetterie classe A, mousseurs économes",
                    "accessibilite": "Sanitaires PMR conformes SIA 500 avec barres d'appui",
                    "extras": "WC lavant en option, sèche-mains air pulsé dans ERP",
                },
                "premium": {
                    "wc": "WC lavant suspendu, réservoir silencieux, plaque design",
                    "lavabo": "Plan vasque sur mesure, mitigeur design certifié",
                    "douche": "Douche à l'italienne, receveur carrelé, robinetterie encastrée",
                    "robinetterie": "Robinetterie haut de gamme, finitions au choix architecte",
                    "accessibilite": "Sanitaires PMR design intégré SIA 500 + Pro Infirmis",
                    "extras": "Système de réutilisation eaux grises, détection de fuite",
                },
            },
            "essais_reception": [
                "Vérification de l'accessibilité PMR selon SIA 500",
                "Test d'étanchéité des appareils et raccordements",
                "Mesure des débits de robinetterie",
            ],
            "normes_referencees": ["SIA 385/1", "SIA 500", "SVGW W3"],
        },
    ],
}

LOT_SANITAIRE = {
    "lot_code": "250",
    "lot_intitule": "Sanitaire",
    "cfc_sections": [CFC_250_SANITAIRE],
    "introduction_lot": (
        "Le présent CCTP du lot 250 Sanitaire couvre la production d'eau chaude sanitaire, "
        "la distribution d'eau froide et chaude, et les évacuations. Les installations "
        "respectent SIA 385/1, SIA 385/2, SVGW W3, SIA 190 et SIA 181 pour les exigences "
        "acoustiques. Les exigences de la LEne pour l'eau chaude solaire sont respectées."
    ),
    "clauses_generales": [
        "Toute la robinetterie est conforme SVGW et listée au registre Eau-Suisse.",
        "Les tests d'étanchéité font l'objet de procès-verbaux signés.",
        "Une analyse bactériologique est effectuée avant mise en service de l'ECS.",
        "Les compteurs sont étalonnés MID et déclarés conformes OIMes.",
    ],
}
