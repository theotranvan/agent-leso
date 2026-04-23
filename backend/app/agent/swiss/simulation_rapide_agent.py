"""Agent simulation énergétique rapide depuis programme architectural.

Sans IFC ni saisie détaillée, estime le besoin de chauffage Qh d'un bâtiment
à partir de son programme (surfaces, affectations, localisation, standard visé).

Usage : phase concours, étude comparative d'enveloppe, chiffrage de principe.
Résultat en 30 secondes — utile aux architectes comme aux thermiciens.

Méthode : formule simplifiée SIA 380/1 basée sur facteur de forme + HDD cantonal
+ compositions type de la bibliothèque.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.connectors.thermic.base import (
    EnergyClass,
    SIA_380_1_DEFAULT_U_VALUES,
    limite_qh_for_affectation,
    qh_to_energy_class,
)
from app.database import get_storage, get_supabase_admin
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


# HDD 20/12 °C (°C·j / an) par station de référence cantonale
HDD_CANTONAL: dict[str, float] = {
    "GE": 3050.0,
    "VD": 3150.0,
    "NE": 3280.0,
    "FR": 3550.0,
    "VS": 3100.0,
    "JU": 3300.0,
    "BE": 3400.0,
    "BS": 2950.0,
    "ZH": 3400.0,
}


# Bibliothèque de compositions type avec U-values indicatives (W/m²·K)
# (cohérent avec app.services.bim.wall_library)
COMPOSITIONS_BY_STANDARD: dict[str, dict[str, float]] = {
    # Standard neuf SIA 380/1 2016
    "sia_380_1_neuf": {
        "wall_external": 0.17,
        "roof": 0.17,
        "slab_ground": 0.25,
        "window": 1.0,
        "door": 1.2,
    },
    # MINERGIE standard
    "minergie": {
        "wall_external": 0.15,
        "roof": 0.12,
        "slab_ground": 0.20,
        "window": 0.85,
        "door": 1.0,
    },
    # MINERGIE-P (haute performance)
    "minergie_p": {
        "wall_external": 0.10,
        "roof": 0.10,
        "slab_ground": 0.15,
        "window": 0.70,
        "door": 0.85,
    },
    # Rénovation qualifiée
    "renovation_qualifiee": {
        "wall_external": 0.25,
        "roof": 0.20,
        "slab_ground": 0.30,
        "window": 1.2,
        "door": 1.4,
    },
    # Existant moyen (avant 1990)
    "existant_1980": {
        "wall_external": 0.60,
        "roof": 0.40,
        "slab_ground": 0.80,
        "window": 2.8,
        "door": 3.0,
    },
}


# Facteurs d'enveloppe typiques (A_enveloppe / SRE) selon forme du bâtiment
FACTEUR_FORME: dict[str, float] = {
    "compact": 0.9,       # immeuble collectif 4-6 étages
    "standard": 1.1,      # villa / petit collectif
    "etale": 1.5,         # villa avec décrochés, plain-pied
    "tres_etale": 2.0,    # villa complexe
}


# Facteur primaire indicatif selon vecteur (SIA 380/1 annexe)
PRIMARY_FACTOR: dict[str, float] = {
    "gaz": 1.05,
    "mazout": 1.10,
    "chauffage_distance": 0.70,
    "pac_air_eau": 0.80,
    "pac_sol_eau": 0.65,
    "pellet": 0.30,
    "buche": 0.20,
    "electrique": 2.00,
    "solaire_thermique": 0.10,
}


# Forfait ECS (kWh/m²·an)
ECS_FORFAIT: dict[str, float] = {
    "logement_individuel": 20.0,
    "logement_collectif": 20.0,
    "administration": 7.0,
    "ecole": 7.0,
    "commerce": 7.0,
    "hopital": 50.0,
    "industriel": 5.0,
    "restauration": 30.0,
    "sport": 20.0,
}


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Calcule Qh + Ep estimatifs depuis un programme.

    Input params :
      - sre_m2: float
      - affectation: 'logement_collectif' | 'logement_individuel' | 'administration' | ...
      - canton: 'GE' | 'VD' | ...
      - standard: 'sia_380_1_neuf' | 'minergie' | 'minergie_p' | 'renovation_qualifiee' | 'existant_1980'
      - operation_type: 'neuf' | 'renovation' | 'existant'
      - heating_vector: 'gaz' | 'pac_sol_eau' | ... (pour Ep)
      - facteur_forme: 'compact' | 'standard' | 'etale' | 'tres_etale' (défaut: standard)
      - fraction_ouvertures: float (défaut: 0.25 = 25% de l'enveloppe en fenêtres)
      - variants: list[dict] (optionnel — comparer plusieurs options)
      - project_name, author
    """
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    sre = float(params.get("sre_m2") or 0)
    if sre <= 0:
        raise ValueError("sre_m2 doit être > 0")

    affectation = str(params.get("affectation", "logement_collectif"))
    canton = str(params.get("canton", "GE")).upper()
    standard = str(params.get("standard", "sia_380_1_neuf"))
    operation_type = str(params.get("operation_type", "neuf"))
    vector = str(params.get("heating_vector", "gaz"))
    facteur_forme = str(params.get("facteur_forme", "standard"))
    fraction_open = float(params.get("fraction_ouvertures", 0.25))

    # Variante principale
    main_variant = _simulate(
        sre_m2=sre,
        affectation=affectation,
        canton=canton,
        standard=standard,
        operation_type=operation_type,
        heating_vector=vector,
        facteur_forme=facteur_forme,
        fraction_ouvertures=fraction_open,
    )

    # Variantes comparatives éventuelles
    variants_results: list[dict[str, Any]] = []
    for v_params in params.get("variants") or []:
        try:
            v = _simulate(
                sre_m2=sre,
                affectation=v_params.get("affectation", affectation),
                canton=v_params.get("canton", canton),
                standard=v_params.get("standard", standard),
                operation_type=v_params.get("operation_type", operation_type),
                heating_vector=v_params.get("heating_vector", vector),
                facteur_forme=v_params.get("facteur_forme", facteur_forme),
                fraction_ouvertures=v_params.get("fraction_ouvertures", fraction_open),
            )
            v["label"] = v_params.get("label") or v_params.get("standard", "variante")
            variants_results.append(v)
        except Exception as exc:
            logger.warning("Variant simulation échec : %s", exc)

    # Rapport markdown
    md = _build_report_md(
        project_name=params.get("project_name", ""),
        main=main_variant,
        variants=variants_results,
        author=params.get("author", ""),
    )

    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(md),
        title="Simulation énergétique rapide",
        subtitle=f"{affectation} — canton {canton}",
        project_name=params.get("project_name", ""),
        author=params.get("author", ""),
        reference=f"SIMRAPIDE-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    storage = get_storage()
    filename = f"simulation_rapide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/simulation_rapide/{task['id']}/{filename}"
    storage.upload(path, pdf_bytes, content_type="application/pdf")
    signed_url = storage.get_signed_url(path, expires_in=604800)

    admin = get_supabase_admin()
    admin.table("documents").insert({
        "organization_id": org_id,
        "project_id": project_id,
        "filename": filename,
        "file_type": "pdf",
        "storage_path": path,
        "processed": True,
    }).execute()

    return {
        "result_url": signed_url,
        "preview": (
            f"Qh estimé: {main_variant['qh_kwh_m2_an']} kWh/m²·an "
            f"(classe {main_variant['energy_class']}) — "
            f"{'conforme' if main_variant['compliant'] else 'NON conforme'} SIA 380/1"
        ),
        "model": None,
        "tokens_used": 0,
        "cost_eur": 0,
        "email_bytes": pdf_bytes,
        "email_filename": filename,
        "main_variant": main_variant,
        "variants": variants_results,
    }


def _simulate(
    sre_m2: float,
    affectation: str,
    canton: str,
    standard: str,
    operation_type: str,
    heating_vector: str,
    facteur_forme: str,
    fraction_ouvertures: float,
) -> dict[str, Any]:
    """Calcul Qh simplifié : pertes_enveloppe · HDD · 24 / SRE / 1000."""
    hdd = HDD_CANTONAL.get(canton, 3200.0)

    # Compositions selon standard
    u_values = COMPOSITIONS_BY_STANDARD.get(standard, COMPOSITIONS_BY_STANDARD["sia_380_1_neuf"])

    # Surface enveloppe estimée à partir du facteur de forme
    fforme = FACTEUR_FORME.get(facteur_forme, 1.1)
    a_enveloppe = sre_m2 * fforme

    # Répartition typique
    share_walls = 0.55
    share_roof = 0.20
    share_slab = 0.20
    share_doors = 0.05

    # Fenêtres prises sur la part murs
    a_walls = a_enveloppe * share_walls * (1 - fraction_ouvertures)
    a_windows = a_enveloppe * share_walls * fraction_ouvertures
    a_roof = a_enveloppe * share_roof
    a_slab = a_enveloppe * share_slab
    a_doors = a_enveloppe * share_doors

    # UA total
    ua = (
        a_walls * u_values["wall_external"]
        + a_windows * u_values["window"]
        + a_roof * u_values["roof"]
        + a_slab * u_values["slab_ground"]
        + a_doors * u_values["door"]
    )

    # Pertes de transmission en kWh/an : UA · HDD · 24 / 1000
    pertes_transmission = ua * hdd * 24 / 1000

    # Apports gratuits (soleil + internes) - facteur indicatif
    apports_gratuits_factor = 0.25 if affectation.startswith("logement") else 0.30
    pertes_nettes = pertes_transmission * (1 - apports_gratuits_factor)

    # Ventilation simplifiée : 0.5 vol/h (logement) ou 1.0 (administration)
    n_vol_h = 1.0 if not affectation.startswith("logement") else 0.5
    # Volume = SRE × 2.8m (hypothèse hauteur moyenne)
    volume = sre_m2 * 2.8
    # Pertes ventilation : V · n · 0.34 · HDD · 24 / 1000 (0.34 = cp·rho air en Wh/m³K)
    pertes_ventilation = volume * n_vol_h * 0.34 * hdd * 24 / 1000

    # Qh total
    qh_total_kwh = pertes_nettes + pertes_ventilation
    qh_kwh_m2_an = qh_total_kwh / sre_m2

    # ECS forfait
    ecs = ECS_FORFAIT.get(affectation, 15.0)

    # Énergie primaire
    primary_factor = PRIMARY_FACTOR.get(heating_vector, 1.0)
    ep_kwh_m2_an = (qh_kwh_m2_an + ecs) * primary_factor

    # Limite SIA 380/1
    qh_limite = limite_qh_for_affectation(affectation)
    compliant = qh_kwh_m2_an <= qh_limite if qh_limite else None

    return {
        "qh_kwh_m2_an": round(qh_kwh_m2_an, 1),
        "qh_mj_m2_an": round(qh_kwh_m2_an * 3.6, 1),
        "ecs_kwh_m2_an": round(ecs, 1),
        "ep_kwh_m2_an": round(ep_kwh_m2_an, 1),
        "qh_limite_kwh_m2_an": qh_limite,
        "compliant": compliant,
        "energy_class": qh_to_energy_class(qh_kwh_m2_an).value,
        "sre_m2": sre_m2,
        "a_enveloppe_m2": round(a_enveloppe, 1),
        "ua_total_wk": round(ua, 2),
        "hdd": hdd,
        "canton": canton,
        "standard": standard,
        "affectation": affectation,
        "heating_vector": heating_vector,
        "facteur_forme": facteur_forme,
        "fraction_ouvertures": fraction_ouvertures,
        "pertes_transmission_kwh": round(pertes_transmission, 0),
        "pertes_ventilation_kwh": round(pertes_ventilation, 0),
        "apports_gratuits_pct": round(apports_gratuits_factor * 100, 0),
    }


def _build_report_md(
    project_name: str,
    main: dict[str, Any],
    variants: list[dict[str, Any]],
    author: str,
) -> str:
    lines = [
        f"# Simulation énergétique rapide — SIA 380/1",
        "",
        f"**Projet** : {project_name or 'Non renseigné'}",
        f"**Date** : {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        f"**Méthode** : calcul forfaitaire simplifié (pertes transmission + ventilation, apports gratuits).",
        f"**À vocation de pré-étude** : ne remplace pas un calcul SIA 380/1 officiel via Lesosai ou équivalent.",
        "",
        "## Variante principale",
        "",
        "| Paramètre | Valeur |",
        "|-----------|--------|",
        f"| Affectation | {main['affectation']} |",
        f"| Canton | {main['canton']} (HDD {main['hdd']}) |",
        f"| Standard visé | {main['standard']} |",
        f"| Vecteur chauffage | {main['heating_vector']} |",
        f"| SRE | {main['sre_m2']} m² |",
        f"| Facteur de forme | {main['facteur_forme']} (A_env ≈ {main['a_enveloppe_m2']} m²) |",
        f"| Fraction ouvertures | {int(main['fraction_ouvertures'] * 100)}% |",
        f"| UA total estimé | {main['ua_total_wk']} W/K |",
        "",
        "## Résultat",
        "",
        "| Indicateur | Valeur | Unité |",
        "|------------|--------|-------|",
        f"| Qh (besoin chauffage) | **{main['qh_kwh_m2_an']}** | kWh/m²·an |",
        f"| Qh (équivalent MJ) | {main['qh_mj_m2_an']} | MJ/m²·an |",
        f"| ECS forfait | {main['ecs_kwh_m2_an']} | kWh/m²·an |",
        f"| Ep (énergie primaire) | {main['ep_kwh_m2_an']} | kWh/m²·an |",
        f"| Limite Qh SIA 380/1 | {main.get('qh_limite_kwh_m2_an', 'n/a')} | kWh/m²·an |",
        f"| Classe énergétique estimée | **{main['energy_class']}** | A→G |",
        f"| Conformité (estimatif) | {'✓ conforme' if main.get('compliant') else '✗ NON conforme' if main.get('compliant') is False else 'indéterminé'} | |",
        "",
        "### Bilan énergie",
        "",
        f"- Pertes par transmission : **{int(main['pertes_transmission_kwh'])} kWh/an**",
        f"- Pertes par ventilation : **{int(main['pertes_ventilation_kwh'])} kWh/an**",
        f"- Apports gratuits pris en compte : **{int(main['apports_gratuits_pct'])}%**",
        "",
    ]

    if variants:
        lines.extend([
            "## Comparatif des variantes",
            "",
            "| Variante | Qh | Ep | Classe | Conformité |",
            "|----------|----|----|--------|------------|",
        ])
        lines.append(
            f"| **Principal** | {main['qh_kwh_m2_an']} | {main['ep_kwh_m2_an']} | "
            f"{main['energy_class']} | {'✓' if main.get('compliant') else '✗' if main.get('compliant') is False else '—'} |"
        )
        for v in variants:
            lines.append(
                f"| {v.get('label', 'Variante')} | {v['qh_kwh_m2_an']} | {v['ep_kwh_m2_an']} | "
                f"{v['energy_class']} | {'✓' if v.get('compliant') else '✗' if v.get('compliant') is False else '—'} |"
            )
        lines.append("")

    lines.extend([
        "## Limites de la méthode",
        "",
        "Cette simulation est un ordre de grandeur basé sur :",
        "- Facteur de forme moyen (A_enveloppe / SRE)",
        "- Compositions type par standard (U-values indicatives)",
        "- HDD cantonal (base 20/12 °C selon SIA 2028)",
        "- Apports gratuits forfaitaires (25-30%)",
        "- Ventilation au taux minimum hygiénique",
        "",
        "Elle **ne remplace pas** un calcul SIA 380/1 officiel dans Lesosai ou équivalent,",
        "qui prend en compte :",
        "- Orientations et masques solaires précis",
        "- Ponts thermiques détaillés (SIA 380/1 annexe B)",
        "- Systèmes CVC réels (rendements, distribution)",
        "- ECS calculée selon usage",
        "- Production EnR sur place",
        "",
        "## Responsabilité",
        "",
        f"Résultat produit par BET Agent. Le thermicien signataire ({author or 'à désigner'}) ",
        "engage seul sa responsabilité sur la conformité du calcul officiel qui sera produit.",
    ])

    return "\n".join(lines)
