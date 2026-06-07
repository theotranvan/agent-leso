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
            "reference": "AEAI 20-15f",
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
            "reference": "AEAI 18-15f",
            "title": "Système d'extinction automatique selon surface et occupation",
            "status": "A_VERIFIER",
            "severity": "IMPORTANT",
        },
        {
            "id": "aeai_hab_m_03",
            "reference": "AEAI 21-15f",
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


# Autorité cantonale de protection incendie compétente (validation du dossier AEAI).
_AUTORITE_CANTONALE = {
    "GE": "OCAS / Police du feu de la Ville (Genève)",
    "VD": "ECA Vaud (Établissement cantonal d'assurance)",
    "NE": "ECAP Neuchâtel",
    "FR": "ECAB Fribourg",
    "VS": "Inspection cantonale du feu (Valais)",
    "JU": "ECA Jura / Police du feu",
    "BE": "GVB / AIB (Berne)",
}

# Mots-clés du contexte particulier → points de vigilance déterministes à ajouter.
# Chaque entrée : (mots-clés, item). On n'invente rien : ce sont des rappels
# standards AEAI, ajoutés seulement si le contexte les mentionne.
_CONTEXT_RULES: list[tuple[tuple[str, ...], dict]] = [
    (("parking", "souterrain", "garage", "véhicule", "vehicule"), {
        "id": "aeai_ctx_parking",
        "reference": "AEAI 15-15f / 18-15f",
        "title": "Parking / sous-sol véhicules : compartimentage EI 90 et désenfumage",
        "description": "Séparation coupe-feu avec les étages, ventilation de désenfumage dimensionnée, "
                       "voies d'évacuation distinctes.",
        "status": "A_VERIFIER",
        "severity": "BLOQUANT",
    }),
    (("poubelle", "déchets", "dechets", "ordures"), {
        "id": "aeai_ctx_dechets",
        "reference": "AEAI 15-15f",
        "title": "Local déchets : isolation coupe-feu et porte EI 30",
        "description": "Local à charge calorifique élevée à compartimenter, porte résistante au feu.",
        "status": "A_VERIFIER",
        "severity": "IMPORTANT",
    }),
    (("vélo", "velo", "cave", "buanderie", "technique"), {
        "id": "aeai_ctx_locaux_annexes",
        "reference": "AEAI 15-15f",
        "title": "Locaux annexes (vélos, caves, technique) compartimentés",
        "description": "Locaux à risque séparés des voies d'évacuation par éléments coupe-feu adaptés.",
        "status": "A_VERIFIER",
        "severity": "IMPORTANT",
    }),
    (("toiture végétalisée", "toiture vegetalisee", "végétalisé", "vegetalise", "panneaux", "photovolt", "solaire"), {
        "id": "aeai_ctx_toiture",
        "reference": "AEAI 13-15f",
        "title": "Toiture (végétalisée / panneaux) : matériaux et propagation en toiture",
        "description": "Comportement au feu de la toiture et des installations en toiture, bandes coupe-feu.",
        "status": "A_VERIFIER",
        "severity": "IMPORTANT",
    }),
    (("commerce", "magasin", "restaurant", "rez commercial", "activité", "activite"), {
        "id": "aeai_ctx_affectation_mixte",
        "reference": "AEAI 16-15f",
        "title": "Affectation mixte : séparation des affectations et évacuations propres",
        "description": "Logement + activité : compartimentage entre affectations et issues indépendantes.",
        "status": "A_VERIFIER",
        "severity": "BLOQUANT",
    }),
]


def _items_canton(canton: str | None) -> list[dict]:
    if not canton:
        return []
    autorite = _AUTORITE_CANTONALE.get(canton.upper())
    if not autorite:
        return []
    return [{
        "id": "aeai_canton_validation",
        "reference": "AEAI 11-15f",
        "title": f"Validation par l'autorité cantonale : {autorite}",
        "description": "Dossier de protection incendie à soumettre à l'autorité compétente du canton "
                       f"{canton.upper()} selon la procédure locale (préavis / autorisation).",
        "status": "A_VERIFIER",
        "severity": "BLOQUANT",
    }]


def _items_context(special_context: str | None) -> list[dict]:
    if not special_context:
        return []
    text = special_context.lower()
    out: list[dict] = []
    for keywords, item in _CONTEXT_RULES:
        if any(kw in text for kw in keywords):
            out.append(item)
    return out


# Mapping des typologies du formulaire vers les clés de la base calibrée
# (checklists_calibrees.py), plus précise et avec références au paragraphe près.
_CALIBRATED_ALIASES = {
    "parking": "parking_souterrain",
    "parking_souterrain": "parking_souterrain",
    "habitation_faible": "habitation_faible",
    "habitation_moyenne": "habitation_moyenne",
    "habitation_elevee": "habitation_elevee",
    "erp_moyen": "erp_moyen",
}

# Catégories à traiter comme bloquantes (les autres → IMPORTANT).
_BLOQUANT_CATEGORIES = {
    "compartimentage", "voies_evacuation", "structure", "structure_portante",
    "parking", "ventilation_desenfumage",
}


def _from_calibrated(building_type: str, canton: str | None) -> list[dict] | None:
    """Convertit la checklist calibrée (si elle couvre la typologie) au format
    attendu par l'UI/route : {id, reference, title, description, status, severity}.

    Renvoie None si la base calibrée ne couvre pas cette typologie."""
    key = _CALIBRATED_ALIASES.get(building_type)
    if not key:
        return None
    try:
        from app.knowledge_base.aeai.checklists_calibrees import get_checklist_aeai
        cl = get_checklist_aeai(key, canton)
    except Exception:
        return None
    if not cl:
        return None

    items: list[dict] = []
    for cat_key, cat in cl["categories"].items():
        severity = "BLOQUANT" if cat_key in _BLOQUANT_CATEGORIES else "IMPORTANT"
        for it in cat["items"]:
            ref = it.get("reference_aeai", "")
            desc_bits = []
            part = it.get(f"particularites_{canton}") if canton else ""
            if part:
                desc_bits.append(part)
            if it.get("documents"):
                desc_bits.append("Pièces : " + ", ".join(it["documents"]))
            items.append({
                "id": it["id"],
                "reference": f"AEAI {ref}" if ref else "AEAI",
                "title": it.get("critere", ""),
                "description": " · ".join(desc_bits),
                "category": cat.get("label", cat_key),
                "status": "A_VERIFIER",
                "severity": severity,
            })
    return items or None


def build_checklist(
    building_type: str,
    height_m: float | None = None,
    nb_occupants: int | None = None,
    canton: str | None = None,
    special_context: str | None = None,
) -> list[dict]:
    """Factory principale : retourne la checklist AEAI appropriée.

    Priorité à la base CALIBRÉE (références AEAI au paragraphe près, critères
    précis ECA-VD / OCAS-GE). Repli sur les templates génériques pour les
    typologies non couvertes. `canton` et `special_context` enrichissent ensuite
    la liste de façon déterministe. Aucun appel LLM.
    """
    items = _from_calibrated(building_type, canton)
    if items is None:
        items = _build_generic(building_type, height_m)

    # Enrichissement déterministe (canton + contexte), sans doublon d'id.
    extra = _items_canton(canton) + _items_context(special_context)
    seen = {i["id"] for i in items}
    for it in extra:
        if it["id"] not in seen:
            items = items + [it]
            seen.add(it["id"])
    return items


def _build_generic(building_type: str, height_m: float | None = None) -> list[dict]:
    """Templates génériques (repli quand la base calibrée ne couvre pas)."""
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
        items = fn(height_m=height_m)
    else:
        items = fn()
    return items


# Alias rétro-compatible : l'agent AEAI importe `get_template_for_building`.
# C'est la même factory que build_checklist (mêmes paramètres).
get_template_for_building = build_checklist
