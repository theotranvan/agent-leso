"""Tests du calcul thermique indicatif SIA 380/1 (saisie manuelle)."""
from __future__ import annotations

import copy

import pytest

from app.connectors.thermic.sia380_simplified import (
    compute_indicative,
    compute_indicative_result,
)

# Bâtiment de référence : immeuble "Les Tilleuls", logement collectif, GE, bien isolé.
TILLEULS = {
    "canton": "GE",
    "affectation": "logement_collectif",
    "zones": [{"name": "Bâtiment", "area": 940, "volume": 2300}],
    "walls": [
        {"type": "mur_exterieur", "area": 456, "u_value": 0.17},
        {"type": "toiture", "area": 345, "u_value": 0.15},
        {"type": "dalle_sur_terrain", "area": 330, "u_value": 0.20},
    ],
    "openings": [{"type": "fenetre", "area": 30, "u_value": 1.0, "g_value": 0.5, "orientation": "S"}],
    "thermal_bridges": [{"type": "balcon", "length": 40, "psi": 0.3}],
}


class TestComputeIndicative:
    def test_batiment_bien_isole_est_conforme(self) -> None:
        r = compute_indicative(TILLEULS)
        # Qh d'un neuf bien isolé : nettement sous la limite logement collectif (44).
        assert 25 <= r["qh_kwh_m2_an"] <= 44
        assert r["compliant"] is True
        assert r["qh_limite_kwh_m2_an"] == 44.0
        assert r["sre_m2"] == 940.0

    def test_mauvaise_isolation_augmente_qh_et_devient_non_conforme(self) -> None:
        bad = copy.deepcopy(TILLEULS)
        for w in bad["walls"]:
            w["u_value"] *= 3
        bad["openings"][0]["u_value"] = 2.8
        rb = compute_indicative(bad)
        rg = compute_indicative(TILLEULS)
        assert rb["qh_kwh_m2_an"] > rg["qh_kwh_m2_an"]
        assert rb["compliant"] is False

    def test_recuperation_chaleur_baisse_qh(self) -> None:
        vent = copy.deepcopy(TILLEULS)
        vent["systems"] = {"ventilation": {"heat_recovery_pct": 80}}
        assert compute_indicative(vent)["qh_kwh_m2_an"] < compute_indicative(TILLEULS)["qh_kwh_m2_an"]

    def test_u_value_manquante_utilise_defaut(self) -> None:
        m = copy.deepcopy(TILLEULS)
        for w in m["walls"]:
            w.pop("u_value", None)
        # Doit calculer sans crash en utilisant les U par défaut SIA.
        assert compute_indicative(m)["qh_kwh_m2_an"] > 0

    def test_sans_zone_leve_valueerror(self) -> None:
        with pytest.raises(ValueError):
            compute_indicative({
                "canton": "GE", "affectation": "logement_collectif",
                "walls": [{"type": "mur_exterieur", "area": 100, "u_value": 0.2}],
            })


class TestComputeIndicativeResult:
    def test_conversion_mj_et_engine_used(self) -> None:
        d = compute_indicative(TILLEULS)
        r = compute_indicative_result(TILLEULS).to_dict()
        assert r["engine_used"] == "sia380_indicatif"
        assert r["qh_mj_m2_an"] == pytest.approx(d["qh_kwh_m2_an"] * 3.6, abs=0.2)
        assert r["compliant"] is True
        assert r["raw_results"]["energy_class"]
