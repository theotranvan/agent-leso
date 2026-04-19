"""Règles et particularités du canton de Genève.

Portée : rôle IDC prépondérant, LDTR pour logement, standards énergétiques,
formulaires OCEN (Office Cantonal de l'Énergie).

Incertitudes explicites :
- Les seuils IDC et obligations CECB peuvent avoir évolué.
- Les sources officielles (ge.ch, OCEN) doivent être consultées en amont de toute démarche réelle.
"""
from typing import Literal

Affectation = Literal["logement_individuel", "logement_collectif", "administration",
                       "commerce", "industriel", "ecole", "hopital", "autre"]

OCEN_URL = "https://www.ge.ch/organisation/office-cantonal-energie-ocen"
LEGIFRANCE_GE_URL = "https://www.ge.ch/legislation"


# Seuils IDC indicatifs - À VALIDER avec documentation OCEN en vigueur
# Ces valeurs servent de cadre logique pour l'agent, pas de référence juridique
IDC_SEUILS_MJ_M2_AN = {
    "logement_collectif": {
        "cible": 450,
        "surconsommation": 600,
        "tres_eleve": 800,
    },
    "logement_individuel": {
        "cible": 500,
        "surconsommation": 650,
        "tres_eleve": 850,
    },
    "administration": {
        "cible": 350,
        "surconsommation": 500,
        "tres_eleve": 700,
    },
    "commerce": {
        "cible": 400,
        "surconsommation": 550,
        "tres_eleve": 750,
    },
    "industriel": {
        "cible": 450,
        "surconsommation": 650,
        "tres_eleve": 900,
    },
}


def idc_status(idc_mj_m2: float, affectation: str) -> dict:
    """Catégorise un IDC selon les seuils indicatifs GE."""
    config = IDC_SEUILS_MJ_M2_AN.get(affectation, IDC_SEUILS_MJ_M2_AN["logement_collectif"])
    if idc_mj_m2 <= config["cible"]:
        return {
            "level": "OK",
            "label": "Dans la cible",
            "color": "green",
            "action": "Aucune action réglementaire",
        }
    if idc_mj_m2 <= config["surconsommation"]:
        return {
            "level": "ATTENTION",
            "label": "Surconsommation modérée",
            "color": "amber",
            "action": "Évaluation recommandée, pistes d'amélioration",
        }
    if idc_mj_m2 <= config["tres_eleve"]:
        return {
            "level": "ALERTE",
            "label": "Surconsommation marquée",
            "color": "orange",
            "action": "Plan d'assainissement énergétique à étudier",
        }
    return {
        "level": "CRITIQUE",
        "label": "Très forte surconsommation",
        "color": "red",
        "action": "Assainissement à planifier - vérifier obligations LEn-GE en vigueur",
    }


# Formulaires OCEN fréquents (pré-remplissage par l'agent)
FORMULAIRES_GE = {
    "idc_annuel": {
        "code": "IDC",
        "label": "Déclaration IDC annuelle",
        "frequency": "annual",
        "submission_deadline_month": 6,  # indicatif
        "required_fields": [
            "ega", "address", "sre_m2", "heating_energy_vector",
            "consumption_raw_value", "consumption_raw_unit",
            "period_start", "period_end", "regie_name",
        ],
    },
    "demande_autorisation_construire": {
        "code": "DAC",
        "label": "Demande d'autorisation de construire (LCI)",
        "required_fields": ["adresse", "parcelle", "zone", "affectation"],
    },
    "justificatif_energie_ge": {
        "code": "EN-101",
        "label": "Justificatif énergétique (LEn-GE)",
        "required_fields": ["affectation", "sre", "standard_vise", "systemes"],
    },
}


# Checklist conformité LEn-GE (à faire compléter par un ingénieur qualifié)
def lci_preflight_checklist(project_data: dict) -> list[dict]:
    """Retourne une checklist de vérifications préalables LCI/LEn-GE pour un projet genevois.

    L'agent produit cette checklist en AMONT du dépôt d'autorisation.
    Chaque point est à CONFIRMER par un professionnel, jamais signé par l'agent.
    """
    is_logement = project_data.get("affectation", "").startswith("logement")
    is_renovation = project_data.get("operation_type") == "renovation"
    is_neuf = project_data.get("operation_type") == "neuf"

    checks = [
        {
            "id": "zone_affectation",
            "title": "Zone d'affectation compatible avec l'usage projeté",
            "reference": "LCI / plan directeur",
            "severity": "BLOQUANT",
            "status": "A_VERIFIER",
        },
        {
            "id": "gabarit",
            "title": "Gabarit conforme (hauteur, distance aux limites)",
            "reference": "LCI art. 21 ss",
            "severity": "BLOQUANT",
            "status": "A_VERIFIER",
        },
        {
            "id": "energie_neuf",
            "title": "Justificatif énergie EN-101 pour construction neuve",
            "reference": "LEn-GE / REn-GE",
            "severity": "BLOQUANT" if is_neuf else "INFO",
            "status": "A_VERIFIER",
            "applicable": is_neuf,
        },
        {
            "id": "cecb_requis",
            "title": "CECB requis selon les cas prévus par la LEn-GE",
            "reference": "LEn-GE / REn-GE",
            "severity": "IMPORTANT",
            "status": "A_VERIFIER",
            "note": "À Genève le CECB n'est pas systématiquement obligatoire. "
                    "Vérifier le cas d'application (subventions, changement usage, transformation majeure).",
        },
        {
            "id": "idc_existant",
            "title": "IDC à jour si bâtiment existant concerné",
            "reference": "REn-GE",
            "severity": "IMPORTANT" if is_renovation else "INFO",
            "status": "A_VERIFIER",
            "applicable": is_renovation,
        },
        {
            "id": "ldtr",
            "title": "Conformité LDTR pour logement (transformation, rénovation)",
            "reference": "LDTR L 5 20",
            "severity": "BLOQUANT" if is_logement and is_renovation else "INFO",
            "status": "A_VERIFIER",
            "applicable": is_logement and is_renovation,
            "note": "Loyers, autorisations spécifiques, préavis locataires.",
        },
        {
            "id": "accessibilite",
            "title": "Accessibilité aux personnes handicapées (LCAP + SIA 500)",
            "reference": "LCAP / SIA 500",
            "severity": "BLOQUANT" if is_neuf else "IMPORTANT",
            "status": "A_VERIFIER",
        },
        {
            "id": "incendie_aeai",
            "title": "Dossier incendie conforme prescriptions AEAI 2015",
            "reference": "AEAI 15-15f",
            "severity": "BLOQUANT",
            "status": "A_VERIFIER",
        },
        {
            "id": "places_stationnement",
            "title": "Places de stationnement et mobilité douce conformes règlement communal",
            "reference": "LCI / règlement communal",
            "severity": "IMPORTANT",
            "status": "A_VERIFIER",
        },
    ]
    return [c for c in checks if c.get("applicable", True)]
