"""Règles spécifiques canton de Vaud.

Sources : prestations.vd.ch, DGE (Direction générale de l'environnement) Vaud.
"""


FORMULAIRES_VD = {
    "cecb_vd": {
        "code": "CECB-VD",
        "label": "Certificat Énergétique Cantonal des Bâtiments",
        "note": "Souvent requis à Vaud lors de transactions ou gros travaux",
    },
    "justificatif_energie_vd": {
        "code": "EN-VD",
        "label": "Justificatif énergétique vaudois",
        "required_fields": ["affectation", "sre", "standard_vise"],
    },
}


def checklist_vd(project_data: dict) -> list[dict]:
    is_renovation = project_data.get("operation_type") == "renovation"
    is_neuf = project_data.get("operation_type") == "neuf"
    return [
        {
            "id": "permis_vd",
            "title": "Permis de construire selon LATC (procédure + communale)",
            "reference": "LATC RSV 700.11",
            "severity": "BLOQUANT",
            "status": "A_VERIFIER",
        },
        {
            "id": "cecb_vd",
            "title": "CECB requis selon cas (transaction, rénovation importante)",
            "reference": "LVLEne / MoPEC vaudois",
            "severity": "IMPORTANT",
            "status": "A_VERIFIER",
        },
        {
            "id": "energie_neuf_vd",
            "title": "Justificatif énergétique VD pour neuf",
            "reference": "LVLEne",
            "severity": "BLOQUANT" if is_neuf else "INFO",
            "status": "A_VERIFIER",
            "applicable": is_neuf,
        },
        {
            "id": "incendie_aeai_vd",
            "title": "Dossier incendie AEAI",
            "reference": "AEAI 15-15f",
            "severity": "BLOQUANT",
            "status": "A_VERIFIER",
        },
    ]
