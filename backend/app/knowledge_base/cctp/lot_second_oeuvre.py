"""Bibliothèque de clauses types CCTP — Lot SECOND ŒUVRE (CFC 271 / 273 / 281 / 285).

Aménagements intérieurs : plâtrerie / cloisons / plafonds, menuiserie intérieure,
revêtements de sol et traitement des surfaces (peinture). Structure CAN (CRB)
adaptée aux pratiques BET romandes. Normes SIA citées par référence.
"""
from __future__ import annotations

# ==========================================================================
# CFC 271 — PLÂTRERIE / CLOISONS / PLAFONDS
# ==========================================================================

CFC_271_PLATRERIE = {
    "cfc": "271",
    "intitule": "Plâtrerie, cloisons légères et plafonds suspendus",
    "articles": [
        {
            "numero": "271.100",
            "titre": "Cloisons légères et doublages",
            "prescriptions": {
                "economique": {
                    "systeme": "Cloison plaque de plâtre sur ossature métallique, simple parement par face",
                    "isolation": "Laine minérale en âme, épaisseur selon hauteur et acoustique visée",
                    "acoustique": "Affaiblissement Rw selon usage (≥ 43 dB entre locaux courants)",
                    "finition": "Joints traités prêts à peindre (niveau Q2)",
                },
                "standard": {
                    "systeme": "Cloison ossature métallique, double parement, plaques adaptées (hydro en locaux humides)",
                    "isolation": "Laine minérale, performances thermo-acoustiques selon SIA 181",
                    "acoustique": "Rw ≥ 52 dB entre logements, ≥ 43 dB entre pièces, justifié par PV d'essai système",
                    "finition": "Joints niveau Q3, traitement des points singuliers (portes, gaines)",
                    "extras": "Renforts pour charges (sanitaires suspendus, radiateurs, meubles)",
                },
                "premium": {
                    "systeme": "Cloison haute performance (parements multiples, plaques haute densité)",
                    "isolation": "Isolation acoustique renforcée, désolidarisation périphérique",
                    "acoustique": "Rw ≥ 57 dB, coupe-feu EI30/EI60 selon AEAI là où exigé",
                    "finition": "Finition niveau Q4 (surfaces en lumière rasante, grands vitrages)",
                    "extras": "Cloisons coupe-feu certifiées, intégration domotique et réservations",
                },
            },
            "essais_reception": [
                "Contrôle de la planéité et de l'aplomb des cloisons",
                "Vérification du niveau de finition des joints (Q2/Q3/Q4)",
                "Contrôle des PV acoustiques et coupe-feu des systèmes posés",
            ],
            "normes_referencees": ["SIA 242 (plâtrerie)", "SIA 181 (acoustique)", "Directive AEAI compartimentage"],
        },
        {
            "numero": "271.200",
            "titre": "Plafonds suspendus",
            "prescriptions": {
                "economique": {
                    "systeme": "Plafond plaque de plâtre sur ossature, hauteur libre selon plans",
                    "finition": "Surface prête à peindre, trappes de visite standard",
                },
                "standard": {
                    "systeme": "Plafond suspendu (plaques ou dalles démontables) avec intégration luminaires/CVC",
                    "acoustique": "Correction acoustique selon usage (dalles absorbantes en bureaux/écoles)",
                    "finition": "Joints soignés, trappes de visite positionnées selon besoins d'exploitation",
                    "extras": "Coordination avec ventilation, sprinklers et éclairage",
                },
                "premium": {
                    "systeme": "Plafond acoustique haute performance ou plafond chauffant/rafraîchissant",
                    "acoustique": "αw ciblé selon SIA 181, traitement des temps de réverbération",
                    "finition": "Calepinage architectural, intégration invisible des équipements",
                    "extras": "Plafonds techniques, îlots acoustiques, plafonds rayonnants",
                },
            },
            "essais_reception": [
                "Contrôle des hauteurs et de la planéité",
                "Vérification de la suspension et des charges admissibles",
                "Réception du calepinage et des trappes de visite",
            ],
            "normes_referencees": ["SIA 242", "SIA 181 (acoustique des locaux)"],
        },
    ],
}


# ==========================================================================
# CFC 273 — MENUISERIE INTÉRIEURE
# ==========================================================================

CFC_273_MENUISERIE = {
    "cfc": "273",
    "intitule": "Menuiserie intérieure (portes, agencements)",
    "articles": [
        {
            "numero": "273.100",
            "titre": "Portes intérieures et blocs-portes",
            "prescriptions": {
                "economique": {
                    "type": "Bloc-porte âme alvéolaire, huisserie bois ou métal, finition stratifié",
                    "quincaillerie": "Ferrage standard, béquille inox, butée",
                    "performance": "Sans exigence feu/acoustique particulière",
                },
                "standard": {
                    "type": "Bloc-porte âme pleine, huisserie réglable, finition mélaminé/placage",
                    "quincaillerie": "Paumelles renforcées, serrure à cylindre, joint acoustique périphérique",
                    "performance": "Portes EI30 et acoustiques (Rw ≥ 32 dB) là où requis (escaliers, logements)",
                    "extras": "Ferme-porte sur portes coupe-feu, signalétique selon AEAI",
                },
                "premium": {
                    "type": "Bloc-porte haute qualité (placage bois noble, affleurant), huisserie invisible",
                    "quincaillerie": "Quincaillerie design, contrôle d'accès intégré, ferrures cachées",
                    "performance": "Portes EI30/EI60 + acoustique Rw ≥ 37 dB, certifiées avec PV",
                    "extras": "Intégration contrôle d'accès, portes coulissantes à galandage",
                },
            },
            "essais_reception": [
                "Contrôle du jeu, de l'aplomb et du fonctionnement des vantaux",
                "Vérification des PV feu/acoustique des blocs-portes concernés",
                "Réception de la quincaillerie et des ferme-portes",
            ],
            "normes_referencees": ["SIA 343 (portes)", "SIA 181 (acoustique)", "Directive AEAI voies d'évacuation"],
        },
    ],
}


# ==========================================================================
# CFC 281 — REVÊTEMENTS DE SOL
# ==========================================================================

CFC_281_SOLS = {
    "cfc": "281",
    "intitule": "Chapes et revêtements de sol",
    "articles": [
        {
            "numero": "281.100",
            "titre": "Chape et revêtements (carrelage, parquet, sol souple)",
            "prescriptions": {
                "economique": {
                    "chape": "Chape ciment sur isolation phonique, planéité standard",
                    "revetement": "Carrelage grès cérame ou sol PVC en lés selon local",
                    "acoustique": "Sous-couche phonique pour bruit de choc (locaux d'habitation)",
                },
                "standard": {
                    "chape": "Chape flottante sur isolation thermo-acoustique, compatible chauffage de sol",
                    "revetement": "Carrelage rectifié / parquet contrecollé / sol souple selon plans",
                    "acoustique": "ΔLw conforme SIA 181 (bruit de choc ≤ 53 dB entre logements)",
                    "extras": "Plinthes assorties, profils de seuil, joints de fractionnement",
                },
                "premium": {
                    "chape": "Chape anhydrite autonivelante haute planéité sur chauffage de sol",
                    "revetement": "Parquet massif / pierre naturelle / résine coulée selon prestige du local",
                    "acoustique": "Performances renforcées, désolidarisation complète",
                    "extras": "Calepinage architectural, traitement des grandes surfaces sans joint apparent",
                },
            },
            "essais_reception": [
                "Mesure de l'humidité résiduelle de la chape avant pose (CM)",
                "Contrôle de la planéité (règle de 2 m) et des pentes en locaux humides",
                "Vérification de la sous-couche acoustique (PV ΔLw)",
                "Réception des joints, seuils et plinthes",
            ],
            "normes_referencees": ["SIA 251 (chapes flottantes)", "SIA 181 (bruit de choc)", "SIA 253 (revêtements sans joints)"],
        },
    ],
}


# ==========================================================================
# CFC 285 — TRAITEMENT DES SURFACES INTÉRIEURES (PEINTURE)
# ==========================================================================

CFC_285_PEINTURE = {
    "cfc": "285",
    "intitule": "Peinture et traitement des surfaces intérieures",
    "articles": [
        {
            "numero": "285.100",
            "titre": "Peinture des murs et plafonds",
            "prescriptions": {
                "economique": {
                    "preparation": "Rebouchage, ponçage, couche d'impression",
                    "finition": "Peinture acrylique mate, 2 couches, teinte blanche",
                    "qualite": "Aspect courant (niveau de finition standard)",
                },
                "standard": {
                    "preparation": "Préparation soignée, enduit de lissage des défauts, impression adaptée au support",
                    "finition": "Peinture lessivable faible émission (label A+/Ecolabel), 2 couches, teintes selon plans",
                    "qualite": "Finition soignée, raccords non visibles",
                    "extras": "Peinture résistante en zones humides / sanitaires, échantillons validés",
                },
                "premium": {
                    "preparation": "Mise à niveau de la subjectile (enduit pelliculaire complet), supports prêts en lumière rasante",
                    "finition": "Peintures haut de gamme / minérales, effets décoratifs selon prescription architecte",
                    "qualite": "Finition irréprochable y compris grandes surfaces et éclairage rasant",
                    "extras": "Traitements spéciaux (anti-graffiti, dépolluant, acoustique), nuancier sur mesure",
                },
            },
            "essais_reception": [
                "Validation des échantillons de teinte et de finition",
                "Contrôle de l'opacité, de l'uniformité et des raccords",
                "Vérification des supports en lumière rasante (selon niveau exigé)",
            ],
            "normes_referencees": ["SIA 257 (travaux de peinture)", "Fiches techniques fabricant", "Exigences COV / labels"],
        },
    ],
}


# ==========================================================================
# REGISTRE LOT SECOND ŒUVRE
# ==========================================================================

LOT_SECOND_OEUVRE = {
    "lot_code": "270",
    "lot_intitule": "Second œuvre — plâtrerie, menuiserie intérieure, sols, peinture",
    "cfc_sections": [
        CFC_271_PLATRERIE,
        CFC_273_MENUISERIE,
        CFC_281_SOLS,
        CFC_285_PEINTURE,
    ],
    "introduction_lot": (
        "Le présent CCTP du lot Second œuvre décrit les prestations d'aménagement "
        "intérieur : plâtrerie, cloisons et plafonds, menuiserie intérieure, chapes et "
        "revêtements de sol, traitement des surfaces. Les exigences acoustiques (SIA 181) "
        "et de protection incendie (directives AEAI) sont respectées selon l'usage des locaux."
    ),
    "clauses_generales": [
        "Les performances acoustiques entre locaux respectent la norme SIA 181 et sont justifiées par PV d'essai des systèmes posés.",
        "Les ouvrages de compartimentage coupe-feu (cloisons, portes) sont certifiés selon les directives AEAI en vigueur.",
        "L'entreprise soumet des échantillons (teintes, revêtements, quincaillerie) à validation avant approvisionnement.",
        "Les supports sont réceptionnés avant intervention (humidité des chapes, planéité, propreté).",
        "Les niveaux de finition (Q2 à Q4, aspect peinture) sont définis par local et contrôlés à la réception.",
    ],
}
