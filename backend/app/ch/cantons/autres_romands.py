"""Règles pour Neuchâtel, Fribourg, Valais, Jura - pré-cadre.

À approfondir par canton dans V3. V2 = cadre minimal.
"""


def checklist_neuchatel(project_data: dict) -> list[dict]:
    return [
        {"id": "permis_ne", "title": "Permis selon droit cantonal neuchâtelois", "severity": "BLOQUANT", "status": "A_VERIFIER"},
        {"id": "cecb_ne", "title": "CECB souvent requis (transactions, subventions)", "severity": "IMPORTANT", "status": "A_VERIFIER"},
        {"id": "incendie_aeai", "title": "Dossier incendie AEAI", "severity": "BLOQUANT", "status": "A_VERIFIER"},
    ]


def checklist_fribourg(project_data: dict) -> list[dict]:
    return [
        {"id": "permis_fr", "title": "Permis selon Loi fribourgeoise", "severity": "BLOQUANT", "status": "A_VERIFIER"},
        {"id": "cecb_fr", "title": "CECB selon cas (subvention, transaction)", "severity": "IMPORTANT", "status": "A_VERIFIER"},
        {"id": "incendie_aeai", "title": "Dossier incendie AEAI", "severity": "BLOQUANT", "status": "A_VERIFIER"},
    ]


def checklist_valais(project_data: dict) -> list[dict]:
    return [
        {"id": "permis_vs", "title": "Permis selon droit valaisan", "severity": "BLOQUANT", "status": "A_VERIFIER"},
        {"id": "cecb_vs", "title": "CECB selon cas", "severity": "IMPORTANT", "status": "A_VERIFIER"},
        {"id": "incendie_aeai", "title": "Dossier incendie AEAI", "severity": "BLOQUANT", "status": "A_VERIFIER"},
    ]


def checklist_jura(project_data: dict) -> list[dict]:
    return [
        {"id": "permis_ju", "title": "Permis selon droit jurassien", "severity": "BLOQUANT", "status": "A_VERIFIER"},
        {"id": "cecb_ju", "title": "CECB selon cas", "severity": "IMPORTANT", "status": "A_VERIFIER"},
        {"id": "incendie_aeai", "title": "Dossier incendie AEAI", "severity": "BLOQUANT", "status": "A_VERIFIER"},
    ]


# Dispatcher
def checklist_for_canton(canton: str, project_data: dict) -> list[dict]:
    """Retourne la checklist appropriée selon le canton."""
    dispatchers = {
        "NE": checklist_neuchatel,
        "FR": checklist_fribourg,
        "VS": checklist_valais,
        "JU": checklist_jura,
    }
    if canton == "GE":
        from app.ch.cantons.geneve import lci_preflight_checklist
        return lci_preflight_checklist(project_data)
    if canton == "VD":
        from app.ch.cantons.vaud import checklist_vd
        return checklist_vd(project_data)
    fn = dispatchers.get(canton)
    if fn:
        return fn(project_data)
    return []
