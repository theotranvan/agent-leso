"""Tests de RÉFÉRENCE des moteurs de calcul — valeurs vérifiables à la main.

Objectif : garantir que les moteurs déterministes (IDC Genève, thermique
SIA 380/1 simplifié, facteurs de combinaison SIA 260) produisent des nombres
JUSTES et ne dérivent jamais silencieusement. Chaque valeur attendue est
calculée à la main dans le commentaire qui précède l'assertion.

Ces tests ne dépendent d'aucun LLM, d'aucun réseau, d'aucune base de données :
ils exercent directement les fonctions de calcul pures.

⚠️ Périmètre : on vérifie l'EXACTITUDE ARITHMÉTIQUE et la COHÉRENCE PHYSIQUE.
La calibration fine d'un calcul SIA 380/1 officiel reste du ressort d'un
thermicien (validation contre Lesosai). Voir les notes `MODELING NOTE`.
"""
from __future__ import annotations

import math

import pytest

# ---------------------------------------------------------------------------
# 1. IDC GENÈVE — formule officielle OCEN, 100 % vérifiable à la main
# ---------------------------------------------------------------------------
from app.connectors.idc.idc_calculator import (
    DJU_NORMAL_GENEVA_COINTRIN,
    MJ_PER_KWH,
    VECTEUR_PCI,
    IDCCalculator,
    IDCComputationInput,
    IDCConsumption,
    IDCStatus,
)


def _idc(vector, value, unit, sre, affectation="logement_collectif", dju=None):
    return IDCCalculator().compute(
        IDCComputationInput(
            sre_m2=sre, vector=vector, affectation=affectation,
            consumptions=[IDCConsumption(raw_value=value, raw_unit=unit)],
            year=2024, dju_year_measured=dju,
        )
    )


class TestIDCReference:
    def test_mazout_pci_exact(self):
        # PCI mazout EL = 9.96 kWh/litre (OFEN).
        # 5000 L × 9.96 = 49 800 kWh ; / 500 m² = 99.6 kWh/m²·an
        r = _idc("mazout", 5000, "litre", 500)
        assert r.total_energy_kwh == pytest.approx(49_800.0, abs=0.1)
        assert r.idc_raw_kwh_m2_an == pytest.approx(99.6, abs=0.01)

    def test_gaz_pci_exact(self):
        # Gaz naturel = 10.26 kWh/m³ (SSIGE).
        # 1000 m³ × 10.26 = 10 260 kWh ; / 200 m² = 51.3 kWh/m²·an
        r = _idc("gaz", 1000, "m3", 200)
        assert r.total_energy_kwh == pytest.approx(10_260.0, abs=0.1)
        assert r.idc_raw_kwh_m2_an == pytest.approx(51.3, abs=0.01)

    def test_mj_conversion_is_exact_x36(self):
        # 1 kWh = 3.6 MJ exactement.
        r = _idc("mazout", 5000, "litre", 500)
        assert r.idc_normalized_mj_m2_an == pytest.approx(
            r.idc_normalized_kwh_m2_an * MJ_PER_KWH, abs=0.01
        )
        assert MJ_PER_KWH == 3.6

    def test_climate_correction_warm_year_scales_up(self):
        # Année chaude : DJU mesurés < DJU normaux → on normalise À LA HAUSSE.
        # correction = 3050 / 2500 = 1.22 ; 99.6 × 1.22 = 121.512 → 121.51
        r = _idc("mazout", 5000, "litre", 500, dju=2500)
        assert r.climate_correction_factor == pytest.approx(3050 / 2500, abs=1e-4)
        assert r.idc_normalized_kwh_m2_an == pytest.approx(121.51, abs=0.02)

    def test_climate_correction_cold_year_scales_down(self):
        # Année froide : DJU mesurés > normaux → normalise À LA BAISSE (< brut).
        r = _idc("mazout", 5000, "litre", 500, dju=3600)
        assert r.climate_correction_factor < 1.0
        assert r.idc_normalized_kwh_m2_an < r.idc_raw_kwh_m2_an

    def test_no_correction_when_dju_absent(self):
        # Sans DJU mesuré : correction = 1.0 → normalisé == brut.
        r = _idc("mazout", 5000, "litre", 500)
        assert r.climate_correction_factor == pytest.approx(1.0, abs=1e-6)
        assert r.idc_normalized_kwh_m2_an == r.idc_raw_kwh_m2_an

    def test_linearity_double_consumption_double_idc(self):
        a = _idc("gaz", 1000, "m3", 300)
        b = _idc("gaz", 2000, "m3", 300)
        assert b.idc_raw_kwh_m2_an == pytest.approx(2 * a.idc_raw_kwh_m2_an, abs=0.01)

    def test_inverse_with_sre(self):
        # IDC ∝ 1/SRE.
        a = _idc("gaz", 1000, "m3", 200)
        b = _idc("gaz", 1000, "m3", 400)
        assert a.idc_raw_kwh_m2_an == pytest.approx(2 * b.idc_raw_kwh_m2_an, abs=0.01)

    def test_kwh_units_passthrough(self):
        # chauffage à distance / élec : déjà en kWh, PCI = 1.0.
        r = _idc("chauffage_distance", 60_000, "kwh", 600)
        assert r.total_energy_kwh == pytest.approx(60_000.0, abs=0.1)
        assert r.idc_raw_kwh_m2_an == pytest.approx(100.0, abs=0.01)

    def test_classification_monotonic(self):
        # IDC croissant ⇒ statut de plus en plus sévère (jamais l'inverse).
        order = [
            IDCStatus.OK, IDCStatus.ATTENTION, IDCStatus.ASSAINISSEMENT_RECOMMANDE,
            IDCStatus.ASSAINISSEMENT_OBLIGATOIRE, IDCStatus.CRITIQUE,
        ]
        last_rank = -1
        for kwh_m2 in [50, 130, 180, 250, 400]:
            # SRE=100 → IDC = conso/100 ; on règle la conso en kWh direct
            r = _idc("chauffage_distance", kwh_m2 * 100, "kwh", 100)
            rank = order.index(r.classification.status)
            assert rank >= last_rank, f"Régression de sévérité à {kwh_m2} kWh/m²"
            last_rank = rank

    def test_invalid_inputs_raise(self):
        with pytest.raises(ValueError):
            _idc("mazout", 5000, "litre", 0)        # SRE nulle
        with pytest.raises(ValueError):
            _idc("vecteur_bidon", 5000, "litre", 500)  # vecteur inconnu
        with pytest.raises(ValueError):
            IDCCalculator().compute(IDCComputationInput(
                sre_m2=500, vector="mazout", affectation="logement_collectif",
                consumptions=[], year=2024))            # aucune conso

    def test_pci_values_within_physical_ranges(self):
        # Garde-fou sur les PCI (kWh/unité) — détecte toute altération grossière.
        assert 9.5 <= VECTEUR_PCI["mazout"][0] <= 10.5     # mazout EL
        assert 9.5 <= VECTEUR_PCI["gaz"][0] <= 11.5        # gaz naturel
        assert 4.5 <= VECTEUR_PCI["pellet"][0] <= 5.5      # granulés bois
        assert DJU_NORMAL_GENEVA_COINTRIN == 3050.0


# ---------------------------------------------------------------------------
# 2. THERMIQUE SIA 380/1 (simplifié) — arithmétique exacte + invariants
# ---------------------------------------------------------------------------
from app.agent.swiss.simulation_rapide_agent import _simulate  # noqa: E402


def _sim(**kw):
    base = dict(
        sre_m2=1000.0, affectation="logement_collectif", canton="GE",
        standard="sia_380_1_neuf", operation_type="neuf", heating_vector="gaz",
        facteur_forme="compact", fraction_ouvertures=0.25,
    )
    base.update(kw)
    return _simulate(**base)


class TestThermiqueReference:
    def test_ua_exact_hand_computation(self):
        """UA recalculé à la main pour le cas de référence.

        SRE=1000, compact (fforme=0.9) → A_env = 900 m²
        parts : murs 0.55, toit 0.20, dalle 0.20, portes 0.05, fenêtres=25% des murs
          A_murs   = 900·0.55·0.75 = 371.25
          A_fen    = 900·0.55·0.25 = 123.75
          A_toit   = 900·0.20      = 180
          A_dalle  = 900·0.20      = 180
          A_portes = 900·0.05      = 45
        U (sia_380_1_neuf): mur .17, fen 1.0, toit .17, dalle .25, porte 1.2
          UA = 371.25·.17 + 123.75·1.0 + 180·.17 + 180·.25 + 45·1.2
             = 63.1125 + 123.75 + 30.6 + 45 + 54 = 316.4625 W/K
        """
        r = _sim()
        assert r["a_enveloppe_m2"] == pytest.approx(900.0, abs=0.1)
        assert r["ua_total_wk"] == pytest.approx(316.46, abs=0.05)

    def test_qh_exact_hand_computation(self):
        """Qh recalculé à la main (cas de référence ci-dessus).

        Transmission : UA·HDD·24/1000 = 316.4625·3050·24/1000 = 23165.06 kWh
        Ventilation : V·n·0.34·HDD·24/1000 ; V=1000·2.8=2800, n=0.5
          = 2800·0.5·0.34·3050·24/1000 = 34843.2 kWh ; récupération 0 % (neuf)
        Apports gratuits logement = 25 %, appliqués au TOTAL des pertes
        (bilan SIA 380/1 : Qh = (Qt + Qv)·(1 − ηg)) :
          Qh = (23165.06 + 34843.2)·0.75 / 1000 = 43.506 → 43.5 kWh/m²·an
        Un neuf SIA 380/1 compact à GE est ainsi conforme (≤ 44).
        """
        r = _sim()
        assert r["pertes_transmission_kwh"] == pytest.approx(23165.0, abs=1.0)
        assert r["pertes_ventilation_kwh"] == pytest.approx(34843.0, abs=1.0)
        assert r["qh_kwh_m2_an"] == pytest.approx(43.5, abs=0.1)
        # MJ = kWh × 3.6
        assert r["qh_mj_m2_an"] == pytest.approx(43.5 * 3.6, abs=0.2)
        # Cohérence physique : un neuf compact GE doit passer la limite SIA (44).
        assert r["compliant"] is True

    def test_ep_exact(self):
        """Ep = (Qh + ECS) × facteur primaire.

        gaz → facteur 1.05 ; ECS logement = 20 kWh/m²·an
        Ep = (43.5 + 20) × 1.05 = 66.675 → 66.7
        """
        r = _sim(heating_vector="gaz")
        assert r["ep_kwh_m2_an"] == pytest.approx((43.5 + 20.0) * 1.05, abs=0.2)

    def test_heat_recovery_reduces_qh(self):
        # MINERGIE-P (récupération 80 %) << neuf sans récupération, même géométrie.
        neuf = _sim()
        mp = _sim(standard="minergie_p", heating_vector="pac_sol_eau")
        assert mp["ventilation_recovery_pct"] == pytest.approx(80.0, abs=0.5)
        assert mp["qh_kwh_m2_an"] < neuf["qh_kwh_m2_an"]

    def test_monotonic_in_uvalue(self):
        # Pire enveloppe ⇒ Qh plus élevé (ordre strict des standards).
        order = ["minergie_p", "minergie", "sia_380_1_neuf",
                 "renovation_qualifiee", "existant_1980"]
        qhs = [_sim(standard=s)["qh_kwh_m2_an"] for s in order]
        assert qhs == sorted(qhs), f"Qh non monotone selon l'enveloppe : {qhs}"

    def test_monotonic_in_hdd(self):
        # Canton plus froid (HDD plus élevé) ⇒ Qh plus élevé.
        ge = _sim(canton="GE")   # 3050
        fr = _sim(canton="FR")   # 3550
        assert fr["hdd"] > ge["hdd"]
        assert fr["qh_kwh_m2_an"] > ge["qh_kwh_m2_an"]

    def test_monotonic_in_form_factor(self):
        compact = _sim(facteur_forme="compact")
        etale = _sim(facteur_forme="tres_etale")
        assert etale["qh_kwh_m2_an"] > compact["qh_kwh_m2_an"]

    def test_all_outputs_finite_and_positive(self):
        r = _sim()
        for k in ("qh_kwh_m2_an", "ep_kwh_m2_an", "ua_total_wk",
                  "pertes_transmission_kwh", "pertes_ventilation_kwh"):
            assert math.isfinite(r[k]) and r[k] > 0, f"{k} = {r[k]}"

    def test_sre_zero_raises_or_zero(self):
        # SRE nulle : ne doit pas planter avec une division silencieuse en NaN/inf.
        with pytest.raises(ZeroDivisionError):
            _sim(sre_m2=0.0)


# ---------------------------------------------------------------------------
# 3. STRUCTURE SIA 260 — facteurs de combinaison + propriétés matériaux
# ---------------------------------------------------------------------------
from app.connectors.structural.saf_generator import (  # noqa: E402
    MATERIAL_PROPERTIES,
    SIA_260_COMBINATIONS,
)


class TestStructureReference:
    def test_uls_fundamental_partial_factors(self):
        """ELU fondamentale SIA 260 : γG = 1.35 (permanent), γQ = 1.5 (variable)."""
        uls = next(c for c in SIA_260_COMBINATIONS if c["id"] == "ULS_STR_FUND")
        factors = {f["case"]: f["factor"] for f in uls["factors"]}
        assert factors["G1"] == 1.35
        assert factors["Q1"] == 1.5

    def test_sls_quasi_permanent_factors(self):
        """ELS quasi-permanente : G à 1.0, Q réduit (ψ2 ≈ 0.3 pour habitation)."""
        sls = next(c for c in SIA_260_COMBINATIONS if c["id"] == "SLS_QP")
        factors = {f["case"]: f["factor"] for f in sls["factors"]}
        assert factors["G1"] == 1.0
        assert factors["Q1"] == pytest.approx(0.3, abs=0.01)

    def test_material_elastic_moduli(self):
        """Modules d'élasticité de référence (GPa) — valeurs normalisées."""
        assert MATERIAL_PROPERTIES["S235"]["E_GPa"] == 210      # acier
        assert MATERIAL_PROPERTIES["S355"]["E_GPa"] == 210
        assert MATERIAL_PROPERTIES["C25/30"]["fck_MPa"] == 25   # béton fck
        assert MATERIAL_PROPERTIES["C30/37"]["fck_MPa"] == 30
        assert MATERIAL_PROPERTIES["S235"]["fy_MPa"] == 235     # limite élastique

    def test_beam_moment_formula_qL2_over_8(self):
        """Vérifie l'identité physique M = q·L²/8 d'une poutre sur 2 appuis,
        avec pondération ELU permanente 1.35.

        q = 10 kN/m permanent, L = 6 m → q_ELU = 13.5 ; M = 13.5·36/8 = 60.75 kNm
        (on recalcule la formule de référence utilisée par le double-check).
        """
        q_char = 10.0
        L = 6.0
        gamma_g = 1.35
        m_expected = (q_char * gamma_g) * L * L / 8.0
        assert m_expected == pytest.approx(60.75, abs=0.01)


# ---------------------------------------------------------------------------
# 4. MÉTRÉS SIA 416 — ratios et table de correspondance IFC→CFC
# ---------------------------------------------------------------------------
from app.agent.swiss.metres_agent import IFC_TO_CFC  # noqa: E402


class TestMetresReference:
    def test_ifc_to_cfc_core_mapping(self):
        # Correspondances structurelles essentielles (CFC eCCC-Bât).
        assert IFC_TO_CFC["IfcSlab"] == "213"      # dalles
        assert IFC_TO_CFC["IfcWall"] == "214"      # murs porteurs
        assert IFC_TO_CFC["IfcRoof"] == "224"      # couverture
        assert IFC_TO_CFC["IfcWindow"] == "221"    # fenêtres
        assert IFC_TO_CFC["IfcDoor"] == "222"      # portes

    def test_all_cfc_codes_are_three_digits(self):
        for ifc, cfc in IFC_TO_CFC.items():
            assert cfc.isdigit() and len(cfc) == 3, f"CFC invalide pour {ifc}: {cfc}"


# ---------------------------------------------------------------------------
# 5. STRUCTURE — MOTEUR RÉEL (double-check M = qL²/8 via parse_csv)
# ---------------------------------------------------------------------------
import csv as _csv  # noqa: E402
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

from app.connectors.structural.results_parser import SafResultsParser  # noqa: E402


def _model_poutre_6m():
    """Poutre simplement appuyée N1(0,0,0)–N2(6,0,0), charge permanente 10 kN/m."""
    return {
        "nodes": [
            {"id": "N1", "x": 0.0, "y": 0.0, "z": 0.0},
            {"id": "N2", "x": 6.0, "y": 0.0, "z": 0.0},
        ],
        "members": [
            {"id": "B1", "type": "beam", "node_start": "N1", "node_end": "N2",
             "section": "HEA200", "material": "S235"},
        ],
        "loads": [
            {"id": "L1", "target": "B1", "type": "uniform_vertical",
             "value_kN_m": 10.0, "category": "Permanent"},
        ],
    }


def _csv_results(rows: list[dict]) -> Path:
    fd = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8")
    writer = _csv.DictWriter(fd, fieldnames=["member_id", "M_kNm", "V_kN", "N_kN"])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    fd.close()
    return Path(fd.name)


class TestStructureEngineReference:
    def test_beam_moment_double_check_exact(self):
        """Le moteur recalcule M = q_ELU·L²/8 et le compare au logiciel.

        q = 10 kN/m permanent → q_ELU = 10·1.35 = 13.5 kN/m, L = 6 m
        M_analytique = 13.5·6²/8 = 60.75 kNm
        Résultat logiciel identique ⇒ écart 0 % ⇒ pas d'anomalie bloquante.
        """
        csv_path = _csv_results([{"member_id": "B1", "M_kNm": 60.75, "V_kN": 40.5, "N_kN": 0}])
        try:
            res = SafResultsParser().parse_csv_results_and_check(csv_path, _model_poutre_6m())
        finally:
            csv_path.unlink(missing_ok=True)
        beam = next(a for a in res.anomalies if a.check_type == "beam_M_qL2_8")
        assert beam.analytical_value == pytest.approx(60.75, abs=0.01)
        assert beam.divergence_pct == pytest.approx(0.0, abs=0.5)

    def test_beam_divergence_flagged(self):
        """Un résultat logiciel franchement faux doit être signalé comme anomalie."""
        csv_path = _csv_results([{"member_id": "B1", "M_kNm": 90.0, "V_kN": 40, "N_kN": 0}])
        try:
            res = SafResultsParser().parse_csv_results_and_check(csv_path, _model_poutre_6m())
        finally:
            csv_path.unlink(missing_ok=True)
        beam = next(a for a in res.anomalies if a.check_type == "beam_M_qL2_8")
        # |60.75 - 90| / 60.75 = 48.1 % → bien au-delà du seuil de 15 %
        assert beam.divergence_pct > 15.0
        assert beam.analytical_value == pytest.approx(60.75, abs=0.01)

    def test_deflection_formula_reference(self):
        """Flèche d'une poutre sur 2 appuis : f = 5·q·L⁴/(384·E·I).

        Référence documentaire (le dimensionnement fin est délégué au logiciel
        externe Scia/RFEM ; cette identité sert de garde-fou de plausibilité).
        q = 10 kN/m = 10e3 N/m, L = 6 m, E = 210e9 Pa (S235),
        I = 3692e-8 m⁴ (HEA200)
        f = 5·10e3·6⁴ / (384·210e9·3692e-8) = 6.48e7 / 2.977e9 ≈ 0.0218 m (21.8 mm)
        """
        q, L, E, inertia = 10e3, 6.0, 210e9, 3692e-8
        f = 5 * q * L**4 / (384 * E * inertia)
        assert f == pytest.approx(0.0218, abs=0.001)


# ---------------------------------------------------------------------------
# 6. MÉTRÉS — MOTEUR RÉEL sur un IFC synthétique à surfaces CONNUES
# ---------------------------------------------------------------------------
from app.agent.swiss.metres_agent import _extract_metres  # noqa: E402


def _build_ifc_with_spaces(spaces):
    """Construit un IFC minimal : 1 étage + N IfcSpace avec quantités connues.

    spaces : liste de (GrossFloorArea, NetFloorArea, NetVolume).
    """
    import ifcopenshell
    import ifcopenshell.api

    f = ifcopenshell.api.run("project.create_file")
    proj = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="REF")
    ifcopenshell.api.run("unit.assign_unit", f)
    ifcopenshell.api.run("context.add_context", f, context_type="Model")
    site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="S")
    bld = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="B")
    storey = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="RDC")
    ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=proj)
    ifcopenshell.api.run("aggregate.assign_object", f, products=[bld], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", f, products=[storey], relating_object=bld)
    for i, (gfa, nfa, nv) in enumerate(spaces):
        sp = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSpace", name=f"L{i}")
        ifcopenshell.api.run("aggregate.assign_object", f, products=[sp], relating_object=storey)
        qto = ifcopenshell.api.run("pset.add_qto", f, product=sp, name="Qto_SpaceBaseQuantities")
        ifcopenshell.api.run("pset.edit_qto", f, qto=qto, properties={
            "GrossFloorArea": gfa, "NetFloorArea": nfa, "NetVolume": nv})
    return f.to_string().encode("utf-8")


class TestMetresEngineReference:
    def test_extracts_known_surfaces(self):
        """SB/SU/volume = somme des quantités des espaces ; SRE = 0.95·SB.

        2 espaces : GFA 100+150 = 250 ; NFA 90+135 = 225 ; NV 280+420 = 700
        SRE attendu = round(250·0.95, 1) = 237.5 m²
        """
        ifc_bytes = _build_ifc_with_spaces([(100.0, 90.0, 280.0), (150.0, 135.0, 420.0)])
        m = _extract_metres(ifc_bytes)
        assert m["sb_m2"] == pytest.approx(250.0, abs=0.1)
        assert m["su_m2"] == pytest.approx(225.0, abs=0.1)
        assert m["volume_m3"] == pytest.approx(700.0, abs=0.1)
        assert m["sre_m2"] == pytest.approx(237.5, abs=0.1)
        assert m["nb_spaces"] == 2

    def test_sre_is_95pct_of_sb(self):
        ifc_bytes = _build_ifc_with_spaces([(400.0, 360.0, 1120.0)])
        m = _extract_metres(ifc_bytes)
        assert m["sre_m2"] == pytest.approx(round(m["sb_m2"] * 0.95, 1), abs=0.1)


# ---------------------------------------------------------------------------
# 7. GARDE-FOUS — l'outil REFUSE une entrée aberrante au lieu de calculer faux
# ---------------------------------------------------------------------------
from pydantic import ValidationError  # noqa: E402

from app.models.thermal import Opening, Wall  # noqa: E402


class TestGuardRails:
    def test_negative_u_value_rejected(self):
        with pytest.raises(ValidationError):
            Wall(area=10.0, u_value=-0.5)

    def test_zero_u_value_rejected(self):
        with pytest.raises(ValidationError):
            Wall(area=10.0, u_value=0.0)

    def test_absurd_u_value_rejected(self):
        with pytest.raises(ValidationError):
            Wall(area=10.0, u_value=999.0)

    def test_valid_u_value_accepted(self):
        assert Wall(area=10.0, u_value=0.17).u_value == 0.17

    def test_g_value_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            Opening(area=5.0, u_value=1.1, g_value=1.5)

    def test_negative_area_rejected(self):
        with pytest.raises(ValidationError):
            Wall(area=-3.0, u_value=0.2)

    def test_idc_rejects_zero_sre(self):
        with pytest.raises(ValueError):
            _idc("mazout", 5000, "litre", 0)

    def test_simulation_rejects_zero_sre(self):
        with pytest.raises(ZeroDivisionError):
            _sim(sre_m2=0.0)
