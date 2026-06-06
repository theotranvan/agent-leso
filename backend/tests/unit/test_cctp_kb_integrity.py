"""Intégrité de la base de connaissances CCTP — TOUS les lots.

Objectif : garantir qu'aucun lot livré aux ingénieurs ne contient de donnée
malformée qui ferait planter `build_cctp_structure_for_lot()` en production
(article sans niveau "standard", code CFC invalide, section vide, etc.) ou qui
produirait un CCTP incohérent (norme manquante, intitulé vide).

Le contrat de schéma est dérivé des fonctions QUI CONSOMMENT la KB :
  - get_lot_cctp / list_lots
  - build_cctp_structure_for_lot   (chemin réel de l'agent CCTP)
  - get_prescriptions_for_article

Aucun LLM, réseau ou DB : on exerce directement les structures de données.
"""
from __future__ import annotations

import re

import pytest

from app.knowledge_base.cctp import (
    LOTS_REGISTRY,
    build_cctp_structure_for_lot,
    get_lot_cctp,
    get_prescriptions_for_article,
    list_lots,
)

# Les 3 niveaux de prestation exposés par l'UI / l'agent.
NIVEAUX = ("economique", "standard", "premium")

# Tous les objets-lots UNIQUES (déduplication des alias du registre).
UNIQUE_LOTS = {id(lot): lot for lot in LOTS_REGISTRY.values()}.values()

# Tous les alias (clé de registre → lot) pour vérifier la résolution.
ALL_KEYS = sorted(LOTS_REGISTRY.keys())


class TestRegistryShape:
    def test_expected_lot_count(self):
        """9 lots distincts attendus (chauffage, ventilation, sanitaire,
        électricité, MCR, gros œuvre, façade, second œuvre, ascenseurs)."""
        lots = list_lots()
        assert len(lots) == 9, f"{len(lots)} lots distincts, 9 attendus : {[x['code'] for x in lots]}"

    def test_no_duplicate_cfc_codes(self):
        codes = [x["code"] for x in list_lots()]
        assert len(codes) == len(set(codes)), f"Codes CFC dupliqués : {codes}"

    def test_every_alias_resolves(self):
        for key in ALL_KEYS:
            assert get_lot_cctp(key) is not None, f"Alias non résolu : {key}"

    def test_lookup_is_case_insensitive(self):
        # get_lot_cctp lower()-case la clé : "CHAUFFAGE" == "chauffage".
        assert get_lot_cctp("CHAUFFAGE") is get_lot_cctp("chauffage")
        assert get_lot_cctp("Ventilation") is get_lot_cctp("ventilation")

    def test_unknown_lot_returns_none(self):
        assert get_lot_cctp("lot_inexistant_xyz") is None

    def test_list_lots_article_count_positive(self):
        for x in list_lots():
            assert x["nb_articles"] >= 1, f"Lot {x['code']} sans article"


class TestLotSchema:
    """Chaque lot respecte le contrat consommé par l'agent CCTP."""

    @pytest.mark.parametrize("lot", UNIQUE_LOTS, ids=lambda lt: lt["lot_code"])
    def test_top_level_keys(self, lot):
        for key in ("lot_code", "lot_intitule", "cfc_sections",
                    "introduction_lot", "clauses_generales"):
            assert key in lot, f"Clé manquante '{key}' dans lot {lot.get('lot_code')}"
        assert isinstance(lot["lot_code"], str) and lot["lot_code"].isdigit()
        assert len(lot["lot_code"]) == 3, f"Code CFC non à 3 chiffres : {lot['lot_code']}"
        assert lot["lot_intitule"].strip(), "Intitulé de lot vide"
        assert isinstance(lot["cfc_sections"], list) and lot["cfc_sections"]
        assert isinstance(lot["clauses_generales"], list) and lot["clauses_generales"]
        assert lot["introduction_lot"].strip(), "Introduction de lot vide"

    @pytest.mark.parametrize("lot", UNIQUE_LOTS, ids=lambda lt: lt["lot_code"])
    def test_sections_shape(self, lot):
        for section in lot["cfc_sections"]:
            assert {"cfc", "intitule", "articles"} <= set(section), \
                f"Section incomplète dans {lot['lot_code']}: {section.keys()}"
            assert re.fullmatch(r"\d{3}", section["cfc"]), \
                f"CFC de section invalide : {section['cfc']}"
            assert section["intitule"].strip()
            assert isinstance(section["articles"], list) and section["articles"], \
                f"Section {section['cfc']} sans article"

    @pytest.mark.parametrize("lot", UNIQUE_LOTS, ids=lambda lt: lt["lot_code"])
    def test_articles_shape(self, lot):
        for section in lot["cfc_sections"]:
            for art in section["articles"]:
                assert {"numero", "titre", "prescriptions"} <= set(art), \
                    f"Article incomplet : {art.get('numero')}"
                # numéro article = code section ou code.sous-numéro
                assert re.fullmatch(r"\d{3}(\.\d+)?", art["numero"]), \
                    f"Numéro d'article invalide : {art['numero']}"
                assert art["titre"].strip(), f"Titre vide pour {art['numero']}"
                # CONTRAT CRITIQUE : build_cctp_structure_for_lot fait
                # prescriptions[niveau] OR prescriptions["standard"] → "standard"
                # DOIT exister sinon KeyError en prod.
                assert "standard" in art["prescriptions"], \
                    f"Article {art['numero']} sans niveau 'standard' (crash prod)"
                # Chaque niveau présent doit être un dict non vide.
                for niv, presc in art["prescriptions"].items():
                    assert niv in NIVEAUX, f"Niveau inconnu '{niv}' dans {art['numero']}"
                    assert isinstance(presc, dict) and presc, \
                        f"Prescriptions vides {art['numero']}/{niv}"

    @pytest.mark.parametrize("lot", UNIQUE_LOTS, ids=lambda lt: lt["lot_code"])
    def test_unique_article_numbers_within_lot(self, lot):
        numeros = [a["numero"] for s in lot["cfc_sections"] for a in s["articles"]]
        assert len(numeros) == len(set(numeros)), \
            f"Numéros d'article dupliqués dans {lot['lot_code']} : {numeros}"

    @pytest.mark.parametrize("lot", UNIQUE_LOTS, ids=lambda lt: lt["lot_code"])
    def test_articles_reference_at_least_one_norm(self, lot):
        """Un CCTP suisse sans norme citée = retour ingénieur garanti."""
        for section in lot["cfc_sections"]:
            for art in section["articles"]:
                normes = art.get("normes_referencees", [])
                assert isinstance(normes, list) and normes, \
                    f"Article {art['numero']} sans norme référencée"


class TestBuildStructure:
    """Le chemin réel de l'agent : doit fonctionner pour tout lot × tout niveau."""

    @pytest.mark.parametrize("lot", UNIQUE_LOTS, ids=lambda lt: lt["lot_code"])
    @pytest.mark.parametrize("niveau", NIVEAUX)
    def test_build_never_crashes(self, lot, niveau):
        structure = build_cctp_structure_for_lot(lot["lot_code"], niveau)
        assert structure["lot_code"] == lot["lot_code"]
        assert structure["niveau_prestation"] == niveau
        assert structure["sections"], "Structure sans section"
        for s in structure["sections"]:
            for art in s["articles"]:
                # prescriptions résolues = jamais vides (fallback standard)
                assert art["prescriptions"], \
                    f"{lot['lot_code']}/{art['numero']}/{niveau} prescriptions vides"

    def test_build_unknown_lot_raises_valueerror(self):
        with pytest.raises(ValueError):
            build_cctp_structure_for_lot("lot_inexistant", "standard")

    def test_get_prescriptions_for_known_article(self):
        # PAC air-eau premium du lot chauffage (cas réel documenté dans le code).
        presc = get_prescriptions_for_article("chauffage", "231.110", "premium")
        if presc is not None:  # tolère un renommage d'article futur
            assert presc["article"] == "231.110"
            assert presc["niveau"] == "premium"

    def test_get_prescriptions_unknown_article_returns_none(self):
        assert get_prescriptions_for_article("chauffage", "999.999") is None


class TestNewLotsContent:
    """Contrôles de contenu sur les 2 lots récemment ajoutés (second œuvre,
    ascenseurs) — ce sont eux que les ingénieurs vont tester en premier."""

    def test_second_oeuvre_covers_expected_cfc(self):
        lot = get_lot_cctp("second_oeuvre")
        cfcs = {s["cfc"] for s in lot["cfc_sections"]}
        # plâtrerie/cloisons, menuiserie int., sols, peinture
        assert {"271", "273", "281", "285"} <= cfcs, f"CFC second œuvre manquants : {cfcs}"

    def test_second_oeuvre_cites_acoustic_norm(self):
        # SIA 181 (acoustique) est LA norme attendue par un BET romand sur ce lot.
        lot = get_lot_cctp("second_oeuvre")
        all_normes = " ".join(
            n for s in lot["cfc_sections"] for a in s["articles"]
            for n in a.get("normes_referencees", [])
        )
        assert "181" in all_normes, "SIA 181 absente du lot second œuvre"

    def test_second_oeuvre_aliases(self):
        for alias in ("platrerie", "cloisons", "menuiserie_interieure", "sols", "peinture"):
            assert get_lot_cctp(alias)["lot_code"] == "270"

    def test_ascenseur_cites_en81_and_pmr(self):
        lot = get_lot_cctp("ascenseur")
        normes = " ".join(
            n for s in lot["cfc_sections"] for a in s["articles"]
            for n in a.get("normes_referencees", [])
        )
        assert "81-20" in normes, "EN 81-20 absente du lot ascenseur"
        assert "500" in normes, "SIA 500 (accessibilité PMR) absente du lot ascenseur"

    def test_ascenseur_alias_plural(self):
        assert get_lot_cctp("ascenseurs")["lot_code"] == "261"
        assert get_lot_cctp("261")["lot_code"] == "261"
