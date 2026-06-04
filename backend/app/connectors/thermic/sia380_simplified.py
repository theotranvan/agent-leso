"""Calcul thermique indicatif SIA 380/1 (stationnaire) à partir de la saisie manuelle.

Ce moteur n'est PAS un calcul officiel : il fournit une estimation d'avant-projet
explicable, qui réagit aux valeurs U/surfaces saisies par l'ingénieur. Le calcul
officiel reste fait et visé dans Lesosai.

Méthode (bilan stationnaire degrés-jours) :

    Qh ≈ (Ht + Hv)·DJ·24/1000/SRE  −  η·(qi + qs)

  - Ht = Σ(U·A·b) parois + Σ(U·A) ouvertures + Σ(ψ·L) ponts thermiques   [W/K]
  - Hv = 0.34·n·V   (renouvellement d'air, réduit si récupération de chaleur)
  - DJ = degrés-jours de chauffage cantonaux (K·jour)
  - qi = apports internes spécifiques ; qs = apports solaires par les ouvertures
  - η  = facteur d'utilisation des apports (simplifié)

Toutes les constantes sont documentées et volontairement prudentes.
"""
from __future__ import annotations

from app.connectors.thermic.base import (
    limite_qh_for_affectation,
    qh_to_energy_class,
)
from app.services.thermique.engine_interface import ThermalEngineResult

# Degrés-jours de chauffage 20/12 indicatifs par canton (K·jour/an).
_DEGRE_JOURS = {"GE": 3050, "VD": 3150, "NE": 3280, "FR": 3550, "VS": 3100, "JU": 3300}
_DJ_DEFAUT = 3200

# Facteur de réduction des pertes b selon l'environnement de la paroi.
_B_FACTEUR = {
    "mur_exterieur": 1.0,
    "toiture": 1.0,
    "plancher": 1.0,
    "dalle_sur_terrain": 0.6,
    "mur_contre_terre": 0.6,
    "dalle_sur_local_non_chauffe": 0.8,
}

# Valeur U par défaut [W/m²·K] si non saisie, selon le type de paroi.
_U_DEFAUT_PAROI = {
    "mur_exterieur": 0.17,
    "toiture": 0.15,
    "dalle_sur_terrain": 0.25,
    "mur_contre_terre": 0.25,
    "dalle_sur_local_non_chauffe": 0.25,
    "plancher": 0.25,
}
_U_DEFAUT_OUVERTURE = 1.2

# Irradiation solaire utile en saison de chauffe [kWh/m²·an] par orientation.
_IRRADIATION = {"S": 270, "E": 155, "O": 155, "N": 100, "horizontal": 220}
_IRRADIATION_DEFAUT = 150

_G_DEFAUT = 0.5            # facteur solaire vitrage si non saisi
_ETA_UTILISATION = 0.9    # facteur d'utilisation des apports (simplifié)
_CAP_AIR = 0.34           # capacité thermique de l'air [Wh/(m³·K)]
_N_BASE = 0.7             # renouvellement d'air hygiénique [1/h]
_N_MIN = 0.15             # infiltration résiduelle plancher [1/h]
_HAUTEUR_ETAGE = 2.8      # hauteur d'étage par défaut pour estimer le volume [m]


def _f(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def compute_indicative(model: dict) -> dict:
    """Retourne le détail du calcul indicatif (en kWh/m²·an) + intermédiaires.

    Lève ValueError si la surface de référence ne peut être déterminée.
    """
    canton = (model.get("canton") or "GE").upper()
    affectation = model.get("affectation") or "logement_collectif"
    is_logement = affectation.startswith("logement")

    zones = model.get("zones") or []
    walls = model.get("walls") or []
    openings = model.get("openings") or []
    bridges = model.get("thermal_bridges") or []

    # --- Surface de référence énergétique (SRE) et volume chauffé ---
    sre = sum(_f(z.get("area")) for z in zones)
    if sre <= 0:
        # Repli : surfaces de plancher déclarées comme parois
        sre = sum(_f(w.get("area")) for w in walls
                  if w.get("type") in ("dalle_sur_terrain", "plancher"))
    if sre <= 0:
        raise ValueError("SRE indéterminée : ajoutez au moins une zone avec une surface.")

    volume = sum(_f(z.get("volume")) for z in zones)
    if volume <= 0:
        volume = sre * _HAUTEUR_ETAGE

    # --- Coefficient de transmission Ht [W/K] ---
    ht_parois = 0.0
    for w in walls:
        area = _f(w.get("area"))
        if area <= 0:
            continue
        wtype = w.get("type") or "mur_exterieur"
        u = _f(w.get("u_value")) or _U_DEFAUT_PAROI.get(wtype, 0.25)
        b = _B_FACTEUR.get(wtype, 1.0)
        ht_parois += u * area * b

    ht_ouvertures = sum(
        _f(o.get("area")) * (_f(o.get("u_value")) or _U_DEFAUT_OUVERTURE)
        for o in openings if _f(o.get("area")) > 0
    )
    ht_ponts = sum(_f(b.get("psi")) * _f(b.get("length")) for b in bridges)
    ht = ht_parois + ht_ouvertures + ht_ponts

    # --- Coefficient de ventilation Hv [W/K] ---
    systems = model.get("systems") or {}
    ventilation = systems.get("ventilation") if isinstance(systems, dict) else None
    hr_pct = _f((ventilation or {}).get("heat_recovery_pct")) if isinstance(ventilation, dict) else 0.0
    n_eff = max(_N_MIN, _N_BASE * (1 - 0.9 * hr_pct / 100.0))
    hv = _CAP_AIR * n_eff * volume

    # --- Pertes totales (transmission + ventilation) ---
    dj = _DEGRE_JOURS.get(canton, _DJ_DEFAUT)
    pertes_kwh = (ht + hv) * dj * 24 / 1000.0
    q_pertes_spec = pertes_kwh / sre

    # --- Apports solaires (ouvertures) ---
    q_sol_kwh = 0.0
    for o in openings:
        area = _f(o.get("area"))
        if area <= 0:
            continue
        g = _f(o.get("g_value")) or _G_DEFAUT
        irr = _IRRADIATION.get(o.get("orientation"), _IRRADIATION_DEFAUT)
        q_sol_kwh += area * g * irr
    q_sol_spec = q_sol_kwh / sre

    # --- Apports internes spécifiques ---
    q_int_spec = 22.0 if is_logement else 15.0

    # --- Besoin de chauffage ---
    q_apports = _ETA_UTILISATION * (q_int_spec + q_sol_spec)
    qh = max(0.0, q_pertes_spec - q_apports)

    # --- ECS + énergie de chauffe totale ---
    qww = 21.0 if is_logement else 7.0
    e_finale = qh + qww

    limite = limite_qh_for_affectation(affectation)
    compliant = (qh <= limite) if limite else None

    return {
        "qh_kwh_m2_an": round(qh, 1),
        "qww_kwh_m2_an": round(qww, 1),
        "e_kwh_m2_an": round(e_finale, 1),
        "qh_limite_kwh_m2_an": round(limite, 1) if limite else None,
        "compliant": compliant,
        "energy_class": qh_to_energy_class(qh).value,
        "sre_m2": round(sre, 1),
        "volume_m3": round(volume, 1),
        "ht_w_k": round(ht, 1),
        "hv_w_k": round(hv, 1),
        "n_eff_1_h": round(n_eff, 2),
        "degre_jours": dj,
        "q_pertes_spec": round(q_pertes_spec, 1),
        "q_apports_spec": round(q_apports, 1),
        "q_sol_spec": round(q_sol_spec, 1),
    }


def compute_indicative_result(model: dict) -> ThermalEngineResult:
    """Calcul indicatif → ThermalEngineResult (unités MJ/m²·an pour le pipeline)."""
    d = compute_indicative(model)

    def mj(v):
        return round(v * 3.6, 1) if v is not None else None

    return ThermalEngineResult(
        qh_mj_m2_an=mj(d["qh_kwh_m2_an"]),
        qww_mj_m2_an=mj(d["qww_kwh_m2_an"]),
        e_mj_m2_an=mj(d["e_kwh_m2_an"]),
        qh_limite_mj_m2_an=mj(d["qh_limite_kwh_m2_an"]),
        compliant=d["compliant"],
        engine_used="sia380_indicatif",
        warnings=[
            "Calcul indicatif d'avant-projet (bilan stationnaire degrés-jours), "
            "non équivalent à un calcul SIA 380/1 officiel. Le justificatif officiel "
            "se fait dans Lesosai.",
        ],
        raw_results=d,
    )
