"""Bibliothèque CCTP — registre central par lot.

Usage:
    from app.knowledge_base.cctp import get_lot_cctp, list_lots

    lot = get_lot_cctp("chauffage")  # ou "230"
    # → dict avec cfc_sections, articles, prescriptions par niveau, normes, essais

Cette bibliothèque alimente l'agent CCTP avec des données structurées RÉELLES
(prescriptions techniques par CFC, normes référencées, essais de réception).
Le LLM ne génère plus du texte ex nihilo : il assemble et contextualise ces
clauses pour le projet spécifique.
"""
from __future__ import annotations

from typing import Literal

from app.knowledge_base.cctp.lot_chauffage import LOT_CHAUFFAGE
from app.knowledge_base.cctp.lot_ventilation import LOT_VENTILATION
from app.knowledge_base.cctp.lot_sanitaire import LOT_SANITAIRE
from app.knowledge_base.cctp.lot_electricite import LOT_ELECTRICITE
from app.knowledge_base.cctp.lot_mcr import LOT_MCR


# Registre principal : tous les lots disponibles
LOTS_REGISTRY = {
    "chauffage": LOT_CHAUFFAGE,
    "230": LOT_CHAUFFAGE,
    "cvs": LOT_CHAUFFAGE,  # alias pour CVS combiné chauffage

    "ventilation": LOT_VENTILATION,
    "244": LOT_VENTILATION,

    "sanitaire": LOT_SANITAIRE,
    "250": LOT_SANITAIRE,

    "electricite": LOT_ELECTRICITE,
    "240": LOT_ELECTRICITE,

    "mcr": LOT_MCR,
    "245": LOT_MCR,
    "gtb": LOT_MCR,
}


LotKey = str
NiveauPrestation = Literal["economique", "standard", "premium"]


def get_lot_cctp(lot_key: LotKey) -> dict | None:
    """Retourne la fiche CCTP complète d'un lot.

    Args:
        lot_key: code CFC (230, 240...), nom du lot (chauffage, sanitaire...), ou alias.

    Returns:
        Dictionnaire avec `lot_code`, `lot_intitule`, `cfc_sections`,
        `introduction_lot`, `clauses_generales`. None si lot inconnu.
    """
    return LOTS_REGISTRY.get(lot_key.lower())


def list_lots() -> list[dict]:
    """Retourne la liste des lots disponibles avec leur code CFC."""
    seen_codes = set()
    out = []
    for key, lot in LOTS_REGISTRY.items():
        if lot["lot_code"] not in seen_codes:
            seen_codes.add(lot["lot_code"])
            out.append({
                "code": lot["lot_code"],
                "intitule": lot["lot_intitule"],
                "key": key,
                "nb_articles": sum(len(s["articles"]) for s in lot["cfc_sections"]),
            })
    return out


def get_prescriptions_for_article(
    lot_key: LotKey,
    article_numero: str,
    niveau: NiveauPrestation = "standard",
) -> dict | None:
    """Retourne les prescriptions d'un article spécifique au niveau demandé.

    Exemple: get_prescriptions_for_article("chauffage", "231.110", "premium")
    → prescriptions PAC air-eau premium.
    """
    lot = get_lot_cctp(lot_key)
    if not lot:
        return None
    for section in lot["cfc_sections"]:
        for article in section["articles"]:
            if article["numero"] == article_numero:
                return {
                    "article": article["numero"],
                    "titre": article["titre"],
                    "niveau": niveau,
                    "prescriptions": article["prescriptions"].get(niveau, {}),
                    "essais_reception": article.get("essais_reception", []),
                    "normes_referencees": article.get("normes_referencees", []),
                    "autorisations": article.get("autorisations", {}),
                }
    return None


def build_cctp_structure_for_lot(
    lot_key: LotKey,
    niveau: NiveauPrestation = "standard",
) -> dict:
    """Construit la structure complète d'un CCTP pour un lot, niveau donné.

    Retourne un dict avec toutes les données dont l'agent a besoin pour produire
    un CCTP de qualité professionnelle. C'est cette fonction qui sera appelée
    par l'agent CCTP, qui contextualisera ensuite avec le projet.
    """
    lot = get_lot_cctp(lot_key)
    if not lot:
        raise ValueError(f"Lot inconnu : {lot_key}. Disponibles : {list(LOTS_REGISTRY.keys())}")

    return {
        "lot_code": lot["lot_code"],
        "lot_intitule": lot["lot_intitule"],
        "niveau_prestation": niveau,
        "introduction": lot["introduction_lot"],
        "clauses_generales": lot["clauses_generales"],
        "sections": [
            {
                "cfc": section["cfc"],
                "intitule": section["intitule"],
                "articles": [
                    {
                        "numero": art["numero"],
                        "titre": art["titre"],
                        "prescriptions": art["prescriptions"].get(niveau, art["prescriptions"]["standard"]),
                        "essais_reception": art.get("essais_reception", []),
                        "normes_referencees": art.get("normes_referencees", []),
                        "autorisations": art.get("autorisations", {}),
                    }
                    for art in section["articles"]
                ],
            }
            for section in lot["cfc_sections"]
        ],
    }
