"""Tests de l'enrichissement déterministe des checklists AEAI (canton + contexte)."""
from __future__ import annotations

from app.ch.aeai_templates import build_checklist


def _ids(items: list[dict]) -> set[str]:
    return {i["id"] for i in items}


class TestCantonEnrichment:
    def test_canton_ge_ajoute_item_autorite(self) -> None:
        base = build_checklist("habitation_moyenne")
        enriched = build_checklist("habitation_moyenne", canton="GE")
        assert len(enriched) == len(base) + 1
        item = next(i for i in enriched if i["id"] == "aeai_canton_validation")
        assert "OCAS" in item["title"]

    def test_canton_vd_reference_eca(self) -> None:
        enriched = build_checklist("habitation_faible", canton="VD")
        item = next(i for i in enriched if i["id"] == "aeai_canton_validation")
        assert "ECA Vaud" in item["title"]

    def test_canton_inconnu_n_ajoute_rien(self) -> None:
        base = build_checklist("habitation_faible")
        enriched = build_checklist("habitation_faible", canton="XX")
        assert len(enriched) == len(base)

    def test_sans_canton_aucun_ajout(self) -> None:
        base = build_checklist("habitation_faible")
        assert "aeai_canton_validation" not in _ids(base)


class TestContextEnrichment:
    def test_parking_ajoute_point_parking(self) -> None:
        enriched = build_checklist(
            "habitation_moyenne",
            special_context="parking souterrain sur 2 niveaux avec accès véhicules",
        )
        assert "aeai_ctx_parking" in _ids(enriched)

    def test_plusieurs_mots_cles_plusieurs_points(self) -> None:
        enriched = build_checklist(
            "habitation_moyenne",
            special_context="parking souterrain, local poubelles, locaux vélos, toiture végétalisée",
        )
        ids = _ids(enriched)
        assert {"aeai_ctx_parking", "aeai_ctx_dechets", "aeai_ctx_locaux_annexes", "aeai_ctx_toiture"} <= ids

    def test_contexte_vide_aucun_ajout(self) -> None:
        base = build_checklist("habitation_faible")
        enriched = build_checklist("habitation_faible", special_context="")
        assert len(enriched) == len(base)

    def test_contexte_non_pertinent_aucun_ajout(self) -> None:
        base = build_checklist("habitation_faible")
        enriched = build_checklist("habitation_faible", special_context="bâtiment classique sans particularité")
        assert len(enriched) == len(base)


class TestNoDuplication:
    def test_pas_de_doublon_id(self) -> None:
        enriched = build_checklist(
            "parking_souterrain",
            canton="GE",
            special_context="parking souterrain véhicules",
        )
        ids = [i["id"] for i in enriched]
        assert len(ids) == len(set(ids))

    def test_combinaison_canton_et_contexte(self) -> None:
        base = build_checklist("habitation_elevee")
        enriched = build_checklist(
            "habitation_elevee",
            canton="FR",
            special_context="parking souterrain",
        )
        # +1 canton, +1 parking
        assert len(enriched) == len(base) + 2
        assert "ECAB" in next(i for i in enriched if i["id"] == "aeai_canton_validation")["title"]
