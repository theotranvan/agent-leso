"""Bibliothèque de clauses types CCTP — Lot FAÇADE / ENVELOPPE (CFC 215).

Isolation périphérique extérieure, fenêtres et portes extérieures, étanchéité de
toiture. Structure CAN (CRB) adaptée aux pratiques BET romandes. Normes SIA citées
par référence (jamais reproduites). Cohérent avec le justificatif SIA 380/1.
"""
from __future__ import annotations

# ==========================================================================
# CFC 226 — ISOLATION PÉRIPHÉRIQUE CRÉPIE (ITE)
# ==========================================================================

CFC_226_ITE = {
    "cfc": "226",
    "intitule": "Isolation périphérique extérieure crépie",
    "articles": [
        {
            "numero": "226.100",
            "titre": "Système d'isolation thermique extérieure crépi (ITE)",
            "prescriptions": {
                "economique": {
                    "isolant": "EPS λ ≤ 0.034 W/mK, épaisseur selon justificatif SIA 380/1 (U paroi visé)",
                    "fixation": "Collage + chevillage selon agrément technique du système",
                    "finition": "Crépi minéral ou organique, grain et teinte selon plans façade",
                    "systeme": "Système ETICS sous agrément (homologation système complet)",
                },
                "standard": {
                    "isolant": "Laine de roche ou EPS λ ≤ 0.032 W/mK, épaisseur pour U ≤ 0.17 W/m²K (neuf)",
                    "fixation": "Collage + chevillage à rupture de pont thermique, profilés de départ alu",
                    "finition": "Crépi de finition résistant aux algues, armature treillis sur toute surface",
                    "systeme": "Système ETICS complet sous agrément, traitement des points singuliers (tableaux, appuis)",
                    "extras": "Mouchoirs d'armature aux angles d'ouvertures, profilés goutte d'eau",
                },
                "premium": {
                    "isolant": "Laine de roche λ ≤ 0.034 (incombustible A1) ou isolant biosourcé, U ≤ 0.15 W/m²K",
                    "fixation": "Fixation mécanique calculée à la pression au vent SIA 261, sans pont thermique",
                    "finition": "Crépi haute durabilité ou parement (briquettes/pierre), échantillon de référence validé",
                    "systeme": "Système ETICS résistant au feu selon AEAI (bandes coupe-feu laine de roche par étage)",
                    "extras": "Bandes coupe-feu AEAI, traitement acoustique, étude des dilatations",
                },
            },
            "essais_reception": [
                "Contrôle de la planéité et de l'épaisseur d'isolant",
                "Test d'arrachement des chevilles (selon agrément système)",
                "Contrôle de la continuité de l'isolation (thermographie IR)",
                "Réception des points singuliers (appuis, tableaux, raccords toiture)",
            ],
            "normes_referencees": ["SIA 243 (crépis)", "SIA 380/1 (thermique)", "SIA 261 (vent)", "Directive AEAI façades"],
        },
    ],
}


# ==========================================================================
# CFC 221 — FENÊTRES ET PORTES EXTÉRIEURES
# ==========================================================================

CFC_221_FENETRES = {
    "cfc": "221",
    "intitule": "Fenêtres et portes extérieures",
    "articles": [
        {
            "numero": "221.100",
            "titre": "Fenêtres (bois-métal / PVC / aluminium)",
            "prescriptions": {
                "economique": {
                    "vitrage": "Double vitrage isolant Ug ≤ 1.0 W/m²K, intercalaire warm-edge",
                    "uw": "Uw ≤ 1.3 W/m²K (fenêtre complète) selon EN 14351-1",
                    "etancheite": "Classe d'étanchéité air/eau selon exposition (EN 12207/12208)",
                    "quincaillerie": "Quincaillerie oscillo-battante, sécurité de base",
                },
                "standard": {
                    "vitrage": "Triple vitrage Ug ≤ 0.7 W/m²K, facteur solaire g adapté à l'orientation",
                    "uw": "Uw ≤ 1.0 W/m²K, valeur cohérente avec le justificatif SIA 380/1",
                    "etancheite": "Classe 4 air / 9A eau / C5 vent selon EN 14351-1, pose en applique étanchée",
                    "quincaillerie": "Oscillo-battant multipoints, sécurité anti-effraction RC2 au rez",
                    "extras": "Joints de pose à étanchéité durable (intérieur étanche, extérieur ouvert à la diffusion)",
                },
                "premium": {
                    "vitrage": "Triple vitrage Ug ≤ 0.5 W/m²K, sélectif, contrôle solaire et acoustique selon SIA 181",
                    "uw": "Uw ≤ 0.8 W/m²K, pose au nu de l'isolant (rupture de pont thermique)",
                    "etancheite": "Classe maximale, test d'étanchéité in situ, bande EPDM précomprimée",
                    "quincaillerie": "Anti-effraction RC2/RC3, ferrures cachées, ventilation contrôlée intégrée",
                    "extras": "Mesure de la perméabilité à l'air du bâtiment (blower-door) après pose",
                },
            },
            "essais_reception": [
                "Vérification des valeurs Uw / Ug sur fiches techniques et étiquettes",
                "Contrôle de l'étanchéité de la pose (eau / air)",
                "Essai blower-door du bâtiment si requis (Minergie / standard visé)",
                "Réception des appuis, tableaux et raccords d'étanchéité",
            ],
            "normes_referencees": ["SIA 331 (fenêtres)", "EN 14351-1", "SIA 380/1", "SIA 181 (acoustique)"],
        },
    ],
}


# ==========================================================================
# CFC 224 — ÉTANCHÉITÉ DE TOITURE
# ==========================================================================

CFC_224_TOITURE = {
    "cfc": "224",
    "intitule": "Étanchéité de toiture",
    "articles": [
        {
            "numero": "224.100",
            "titre": "Toiture plate (étanchéité bitumineuse ou synthétique)",
            "prescriptions": {
                "economique": {
                    "isolation": "Isolant en toiture λ adapté pour U ≤ 0.20 W/m²K, pente minimale 1.5%",
                    "etancheite": "Étanchéité bicouche bitumineuse ou monocouche synthétique selon SIA 271",
                    "protection": "Lestage gravier ou autoprotection, relevés ≥ 15 cm",
                },
                "standard": {
                    "isolation": "Isolant pour U ≤ 0.17 W/m²K, pare-vapeur dimensionné, pente ≥ 2%",
                    "etancheite": "Étanchéité selon SIA 271, relevés ≥ 15 cm, traitement des pénétrations",
                    "protection": "Toiture végétalisée extensive ou dalles sur plots selon usage",
                    "extras": "Garde-corps / lignes de vie selon SUVA, contrôle d'écoulement (test à l'eau)",
                },
                "premium": {
                    "isolation": "Isolant haute performance pour U ≤ 0.15 W/m²K, étude du risque de condensation",
                    "etancheite": "Étanchéité haute durabilité avec détection de fuite intégrée (electronic leak detection)",
                    "protection": "Toiture végétalisée intensive ou panneaux solaires intégrés, rétention d'eau",
                    "extras": "Garde-corps architectural, surveillance d'étanchéité, garantie étendue",
                },
            },
            "essais_reception": [
                "Test d'étanchéité à l'eau (mise en eau ou détection électronique)",
                "Contrôle des relevés et des pénétrations",
                "Réception des dispositifs de sécurité (garde-corps, lignes de vie SUVA)",
            ],
            "normes_referencees": ["SIA 271 (étanchéité)", "SIA 380/1", "SIA 261 (vent/neige)", "Directives SUVA"],
        },
    ],
}


# ==========================================================================
# REGISTRE LOT FAÇADE / ENVELOPPE
# ==========================================================================

LOT_FACADE = {
    "lot_code": "215",
    "lot_intitule": "Façade et enveloppe — isolation, fenêtres, toiture",
    "cfc_sections": [
        CFC_226_ITE,
        CFC_221_FENETRES,
        CFC_224_TOITURE,
    ],
    "introduction_lot": (
        "Le présent CCTP du lot Façade / Enveloppe décrit les prestations d'isolation "
        "périphérique, de fenêtres et portes extérieures et d'étanchéité de toiture. "
        "Les performances thermiques (valeurs U, Uw) sont cohérentes avec le justificatif "
        "SIA 380/1 du projet. Les ouvrages respectent les normes SIA 243, 271, 331, les "
        "exigences acoustiques SIA 181 et les directives AEAI de protection incendie en façade."
    ),
    "clauses_generales": [
        "Toutes les valeurs U et Uw doivent être justifiées par fiche technique et cohérentes avec le justificatif SIA 380/1.",
        "L'entreprise fournit les détails d'exécution des points singuliers (appuis, tableaux, raccords, acrotères) avant exécution.",
        "L'étanchéité à l'air de l'enveloppe est continue ; un essai blower-door est réalisé si le standard énergétique l'exige.",
        "Les dispositions de protection incendie en façade (bandes coupe-feu) respectent les directives AEAI en vigueur.",
        "Les essais d'étanchéité et réceptions des points singuliers sont consignés au dossier d'ouvrage exécuté (DOE).",
    ],
}
