"""Tests d'intégration simulation_rapide_agent - 100% déterministe, pas de LLM."""
from __future__ import annotations

import pytest

from app.agent.swiss.simulation_rapide_agent import (
    COMPOSITIONS_BY_STANDARD,
    FACTEUR_FORME,
    HDD_CANTONAL,
    PRIMARY_FACTOR,
    _simulate,
)


class TestSimulationRapideDeterministic:
    def test_logement_collectif_geneve_sia_380_1_neuf(self) -> None:
        """Variante canonique : logement collectif neuf à Genève, SIA 380/1."""
        r = _simulate(
            sre_m2=1250.0,
            affectation="logement_collectif",
            canton="GE",
            standard="sia_380_1_neuf",
            operation_type="neuf",
            heating_vector="gaz",
            facteur_forme="compact",
            fraction_ouvertures=0.25,
        )
        # Qh attendu dans la plage réaliste SIA 380/1 pour du neuf compact à GE
        assert 15 <= r["qh_kwh_m2_an"] <= 60, f"Qh={r['qh_kwh_m2_an']} hors plage attendue"
        assert r["energy_class"] in ("A", "B", "C")
        assert r["hdd"] == 3050.0
        assert r["a_enveloppe_m2"] == 1125.0  # 1250 × 0.9 (compact)
        assert r["ep_kwh_m2_an"] > r["qh_kwh_m2_an"]

    def test_renovation_beats_existant(self) -> None:
        """Une rénovation qualifiée doit avoir Qh plus bas qu'un existant 1980."""
        base_args = {
            "sre_m2": 800.0,
            "affectation": "logement_collectif",
            "canton": "VD",
            "operation_type": "renovation",
            "heating_vector": "mazout",
            "facteur_forme": "standard",
            "fraction_ouvertures": 0.2,
        }
        existant = _simulate(standard="existant_1980", **base_args)
        reno = _simulate(standard="renovation_qualifiee", **base_args)
        minergie = _simulate(standard="minergie", **base_args)
        minergie_p = _simulate(standard="minergie_p", **base_args)

        assert existant["qh_kwh_m2_an"] > reno["qh_kwh_m2_an"]
        assert reno["qh_kwh_m2_an"] > minergie["qh_kwh_m2_an"]
        assert minergie["qh_kwh_m2_an"] > minergie_p["qh_kwh_m2_an"]

    def test_facteur_forme_impacts_qh(self) -> None:
        """Plus étalé = plus de pertes."""
        base_args = {
            "sre_m2": 200.0,
            "affectation": "logement_individuel",
            "canton": "GE",
            "standard": "sia_380_1_neuf",
            "operation_type": "neuf",
            "heating_vector": "pac_sol_eau",
            "fraction_ouvertures": 0.25,
        }
        compact = _simulate(facteur_forme="compact", **base_args)
        etale = _simulate(facteur_forme="tres_etale", **base_args)
        assert etale["qh_kwh_m2_an"] > compact["qh_kwh_m2_an"]
        assert etale["a_enveloppe_m2"] > compact["a_enveloppe_m2"]

    def test_canton_impacts_hdd(self) -> None:
        """Fribourg (HDD 3550) a plus de pertes que Genève (HDD 3050)."""
        base_args = {
            "sre_m2": 500.0,
            "affectation": "logement_collectif",
            "standard": "sia_380_1_neuf",
            "operation_type": "neuf",
            "heating_vector": "gaz",
            "facteur_forme": "standard",
            "fraction_ouvertures": 0.25,
        }
        ge = _simulate(canton="GE", **base_args)
        fr = _simulate(canton="FR", **base_args)
        assert fr["hdd"] > ge["hdd"]
        assert fr["qh_kwh_m2_an"] > ge["qh_kwh_m2_an"]

    def test_primary_factor_varies_by_vector(self) -> None:
        """Ep dépend du vecteur énergétique via le facteur primaire."""
        base_args = {
            "sre_m2": 500.0,
            "affectation": "logement_collectif",
            "canton": "GE",
            "standard": "sia_380_1_neuf",
            "operation_type": "neuf",
            "facteur_forme": "standard",
            "fraction_ouvertures": 0.25,
        }
        electrique = _simulate(heating_vector="electrique", **base_args)
        pellet = _simulate(heating_vector="pellet", **base_args)
        # Qh identique (que le système), Ep très différent
        assert abs(electrique["qh_kwh_m2_an"] - pellet["qh_kwh_m2_an"]) < 0.1
        assert electrique["ep_kwh_m2_an"] > pellet["ep_kwh_m2_an"] * 3

    def test_energy_class_thresholds(self) -> None:
        """MINERGIE-P doit donner une classe A ou B sur bâtiment compact."""
        r = _simulate(
            sre_m2=1500.0,
            affectation="logement_collectif",
            canton="GE",
            standard="minergie_p",
            operation_type="neuf",
            heating_vector="pac_sol_eau",
            facteur_forme="compact",
            fraction_ouvertures=0.2,
        )
        assert r["energy_class"] in ("A", "B")
        assert r["compliant"] is True

    def test_all_hdd_stations_defined(self) -> None:
        assert "GE" in HDD_CANTONAL and HDD_CANTONAL["GE"] == 3050.0
        assert all(v > 2500 and v < 4000 for v in HDD_CANTONAL.values())

    def test_all_standards_have_all_uvalues(self) -> None:
        required_keys = {"wall_external", "roof", "slab_ground", "window", "door"}
        for std, uvals in COMPOSITIONS_BY_STANDARD.items():
            missing = required_keys - set(uvals.keys())
            assert not missing, f"Standard {std} manque {missing}"

    def test_primary_factor_reasonable_ranges(self) -> None:
        """Les facteurs primaires doivent respecter les plages SIA."""
        # Bois/biomasse doit être très bas
        assert PRIMARY_FACTOR["pellet"] < 0.5
        assert PRIMARY_FACTOR["buche"] < 0.5
        # Électrique > 1.5 en SIA 380/1
        assert PRIMARY_FACTOR["electrique"] >= 1.5
        # PAC entre 0.5 et 1.0
        assert 0.5 < PRIMARY_FACTOR["pac_sol_eau"] < 1.0
