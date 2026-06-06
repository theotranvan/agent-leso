"""Bibliothèque de clauses types CCTP — Lot ASCENSEURS (CFC 261).

Installations de transport vertical (ascenseurs, monte-charges). Normes EN 81-20/50
et SIA 370 citées par référence. Adapté aux pratiques BET romandes.
"""
from __future__ import annotations

# ==========================================================================
# CFC 261 — ASCENSEURS
# ==========================================================================

CFC_261_ASCENSEURS = {
    "cfc": "261",
    "intitule": "Ascenseurs et installations de transport vertical",
    "articles": [
        {
            "numero": "261.100",
            "titre": "Ascenseur électrique sans local des machines (MRL)",
            "prescriptions": {
                "economique": {
                    "type": "Ascenseur électrique à traction sans local des machines (MRL)",
                    "charge": "Charge et nombre de personnes selon trafic (min. 630 kg / 8 pers. pour PMR)",
                    "vitesse": "Vitesse adaptée au nombre de niveaux (0.63–1.0 m/s)",
                    "accessibilite": "Cabine et accès conformes à l'accessibilité PMR (SIA 500)",
                    "finition": "Cabine finition standard, éclairage LED",
                },
                "standard": {
                    "type": "Ascenseur MRL à traction à variation de fréquence (VVVF), entraînement efficient",
                    "charge": "≥ 630 kg / 8 pers., cabine traversante si requis par les plans",
                    "vitesse": "1.0 m/s, précision d'arrêt ≤ ±10 mm",
                    "accessibilite": "Conformité PMR complète (SIA 500), signalisation sonore et visuelle, miroir, main courante",
                    "finition": "Cabine inox/stratifié, éclairage LED, télésurveillance et télé-alarme GSM",
                    "extras": "Manœuvre pompiers si requise, batterie de secours (mise à niveau et ouverture)",
                },
                "premium": {
                    "type": "Ascenseur MRL haut de gamme, régénération d'énergie, gestion de trafic intelligente",
                    "charge": "Dimensionnement selon étude de trafic, cabine(s) multiples coordonnées",
                    "vitesse": "≥ 1.6 m/s, confort de roulement élevé (faibles accélérations)",
                    "accessibilite": "Accessibilité PMR + confort (annonces vocales, écran d'information)",
                    "finition": "Cabine architecturale (verre, pierre, sur mesure), éclairage scénographié",
                    "extras": "Manœuvre pompiers, ascenseur évacuation, contrôle d'accès par étage, supervision GTB",
                },
            },
            "essais_reception": [
                "Réception par organe de contrôle accrédité (mise en service selon ordonnance)",
                "Essais de sécurité : parachute, limiteur de vitesse, freins, fins de course",
                "Contrôle de la précision d'arrêt et du nivelage à chaque palier",
                "Vérification de la télé-alarme (liaison phonique permanente) et de l'éclairage de secours",
                "Contrôle de l'accessibilité PMR (dimensions cabine, commandes, signalisation)",
            ],
            "normes_referencees": [
                "EN 81-20 / EN 81-50 (sécurité ascenseurs)",
                "SIA 370 (ascenseurs)",
                "SIA 500 (constructions sans obstacles)",
                "Ordonnance sur les ascenseurs / Directive Machines",
            ],
        },
    ],
}


# ==========================================================================
# REGISTRE LOT ASCENSEURS
# ==========================================================================

LOT_ASCENSEUR = {
    "lot_code": "261",
    "lot_intitule": "Ascenseurs et transport vertical",
    "cfc_sections": [
        CFC_261_ASCENSEURS,
    ],
    "introduction_lot": (
        "Le présent CCTP du lot Ascenseurs décrit la fourniture, la pose et la mise en "
        "service des installations de transport vertical. Les installations respectent les "
        "normes EN 81-20/50, la norme SIA 370 et les exigences d'accessibilité SIA 500. "
        "La réception est prononcée après contrôle par un organe accrédité."
    ),
    "clauses_generales": [
        "L'installation est conforme aux normes EN 81-20/50 et à la réglementation suisse sur les ascenseurs.",
        "L'accessibilité aux personnes à mobilité réduite est garantie selon la norme SIA 500.",
        "Une liaison phonique de secours permanente (télé-alarme) et un éclairage de secours sont exigés.",
        "La mise en service est subordonnée à la réception par un organe de contrôle accrédité.",
        "Un contrat de maintenance et la garantie des pièces sont précisés dans l'offre.",
    ],
}
