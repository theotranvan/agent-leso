"""Templates de checklists AEAI par typologie de bâtiment.

Les points sont formulés en langage propre (résumés BET) qui RÉFÉRENCENT les directives AEAI
sans les reproduire textuellement. Les normes AEAI payantes ne sont jamais copiées.
"""


def _base_items(building_type: str) -> list[dict]:
    """Points communs à toutes les typologies."""
    return [
        {
            "id": "aeai_01",
            "reference": "AEAI 1-15f",
            "title": "Concept de protection incendie adapté à l'affectation",
            "description": "Vérifier que le concept choisi (standard / avec mesures / cas par cas) est cohérent avec l'affectation et la taille du bâtiment.",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_compartimentage",
            "reference": "AEAI 15-15f",
            "title": "Compartimentage coupe-feu cohérent",
            "description": "Parois et planchers séparatifs avec résistance au feu adaptée au type d'utilisation et à la hauteur.",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_voies_evac",
            "reference": "AEAI 16-15f",
            "title": "Voies d'évacuation dimensionnées et protégées",
            "description": "Longueurs, largeurs, nombre d'issues, désenfumage éventuel selon occupation et étage.",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_eclairage_secu",
            "reference": "AEAI 17-15f",
            "title": "Éclairage de sécurité sur voies d'évacuation",
            "description": "Autonomie et niveau d'éclairement conformes.",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
        {
            "id": "aeai_detection",
            "reference": "AEAI 18-15f",
            "title": "Détection et alarme incendie",
            "description": "Système conforme à l'occupation et à la taille.",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
        {
            "id": "aeai_extincteurs",
            "reference": "AEAI 18-15f",
            "title": "Extincteurs portatifs - répartition et accessibilité",
            "description": "Nombre, type et positionnement appropriés.",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
    ]


def items_habitation_faible(height_m: float | None = None) -> list[dict]:
    """Habitation < 11m."""
    base = _base_items("habitation_faible")
    return base + [
        {
            "id": "aeai_hab_f_01",
            "reference": "AEAI 15-15f",
            "title": "Distances incendie entre bâtiments d'habitation",
            "description": "Respect des distances selon matériaux de façade et de toiture.",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_hab_f_02",
            "reference": "AEAI 15-15f",
            "title": "Cage d'escalier avec résistance au feu adaptée si plus d'un étage",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
    ]


def items_habitation_moyenne() -> list[dict]:
    """Habitation 11-30m."""
    base = _base_items("habitation_moyenne")
    return base + [
        {
            "id": "aeai_hab_m_01",
            "reference": "AEAI 15-15f",
            "title": "Cage d'escalier EI 60 avec sas éventuels",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_hab_m_02",
            "reference": "AEAI 15-15f",
            "title": "Système d'extinction automatique selon surface et occupation",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
        {
            "id": "aeai_hab_m_03",
            "reference": "AEAI 16-15f",
            "title": "Désenfumage cage d'escalier si deux niveaux souterrains ou plus",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
    ]


def items_habitation_elevee() -> list[dict]:
    """Habitation > 30m."""
    base = _base_items("habitation_elevee")
    return base + [
        {
            "id": "aeai_hab_e_01",
            "reference": "AEAI 15-15f",
            "title": "Systèmes sprinkler dans ensemble des espaces habités",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_hab_e_02",
            "reference": "AEAI 15-15f",
            "title": "Ascenseurs pompiers conformes, zone de refuge étagée",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_hab_e_03",
            "reference": "AEAI 15-15f",
            "title": "Compartimentage renforcé EI 90 / R 90",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_hab_e_04",
            "reference": "AEAI 18-15f",
            "title": "Système de détection généralisée avec report CSU",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
    ]


def items_administration() -> list[dict]:
    base = _base_items("administration")
    return base + [
        {
            "id": "aeai_adm_01",
            "reference": "AEAI 15-15f",
            "title": "Distances voies d'évacuation selon effectif par étage",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_adm_02",
            "reference": "AEAI 15-15f",
            "title": "Séparation des zones à occupation différente",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
    ]


def items_erp_petit() -> list[dict]:
    """Lieu de rassemblement ≤ 300 personnes."""
    base = _base_items("erp_petit")
    return base + [
        {
            "id": "aeai_erp_p_01",
            "reference": "AEAI 16-15f",
            "title": "Nombre d'issues ≥ 2, largeur dimensionnée par la charge d'occupation",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_erp_p_02",
            "reference": "AEAI 17-15f",
            "title": "Éclairage de sécurité et signalisation claire",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
    ]


def items_erp_moyen() -> list[dict]:
    """300-1000 personnes."""
    base = items_erp_petit()
    return base + [
        {
            "id": "aeai_erp_m_01",
            "reference": "AEAI 15-15f",
            "title": "Sprinkler ou équivalent selon nature occupation",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
        {
            "id": "aeai_erp_m_02",
            "reference": "AEAI 18-15f",
            "title": "Désenfumage mécanique ou naturel dimensionné",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
    ]


def items_erp_grand() -> list[dict]:
    """> 1000 personnes."""
    base = items_erp_moyen()
    return base + [
        {
            "id": "aeai_erp_g_01",
            "reference": "AEAI 15-15f",
            "title": "Concept global avec expert incendie obligatoire",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_erp_g_02",
            "reference": "AEAI 18-15f",
            "title": "Centrale incendie avec tableau pompiers normalisé",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
    ]


def items_parking_souterrain() -> list[dict]:
    base = _base_items("parking_souterrain")
    return base + [
        {
            "id": "aeai_park_01",
            "reference": "AEAI 15-15f",
            "title": "Séparation EI 90 avec bâtiment attenant, issues distinctes",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_park_02",
            "reference": "AEAI 18-15f",
            "title": "Ventilation de désenfumage dimensionnée",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
    ]


def items_industriel() -> list[dict]:
    base = _base_items("industriel")
    return base + [
        {
            "id": "aeai_ind_01",
            "reference": "AEAI 15-15f",
            "title": "Charge calorifique évaluée, compartimentage en conséquence",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
        {
            "id": "aeai_ind_02",
            "reference": "AEAI 15-15f",
            "title": "Stockage matières dangereuses (liquides inflammables, gaz) conforme",
            "status": "A_VERIFIER",
            "severity": "BLOQUANT",
        },
    ]


def build_checklist(building_type: str, height_m: float | None = None, nb_occupants: int | None = None) -> list[dict]:
    """Factory principale : retourne la checklist AEAI appropriée."""
    dispatch = {
        "habitation_faible": items_habitation_faible,
        "habitation_moyenne": items_habitation_moyenne,
        "habitation_elevee": items_habitation_elevee,
        "administration_faible": items_administration,
        "administration_moyenne": items_administration,
        "administration_elevee": items_administration,
        "ecole": items_administration,
        "erp_petit": items_erp_petit,
        "erp_moyen": items_erp_moyen,
        "erp_grand": items_erp_grand,
        "parking_souterrain": items_parking_souterrain,
        "industriel": items_industriel,
        "depot": items_industriel,
        "hopital": items_erp_grand,
    }
    fn = dispatch.get(building_type, items_administration)

    # Certaines fns acceptent paramètres
    import inspect
    sig = inspect.signature(fn)
    if "height_m" in sig.parameters:
        return fn(height_m=height_m)
    return fn()
