"""Agent thermique CH - pilote le pipeline SIA 380/1."""
import logging
from datetime import datetime
from typing import Any

from app.agent.router import call_llm
from app.agent.swiss.prompts_ch import get_prompt_ch
from app.ch.constants import station_default_for_canton, STATIONS_CLIMATIQUES_SIA_2028
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html, render_visa_block
from app.services.thermique.registry import get_engine

logger = logging.getLogger(__name__)


async def run_thermal_pipeline(
    thermal_model: dict,
    engine_name: str = "lesosai_stub",
    project_name: str = "",
    project_address: str = "",
    author: str = "",
) -> dict:
    """Pipeline thermique complet : préparation → calcul (stub ou file) → note.

    Retourne un dict avec : justificatif_md, pdf_bytes, results, warnings, engine_used
    """
    canton = thermal_model.get("canton") or "GE"
    if "climate" not in thermal_model:
        station = station_default_for_canton(canton)
        thermal_model["climate"] = {
            "station": station,
            **STATIONS_CLIMATIQUES_SIA_2028.get(station, {}),
        }

    engine = get_engine(engine_name)

    # Préparation
    prepared = await engine.prepare_model(thermal_model)
    warnings = prepared.get("warnings", [])

    # Calcul si stub (sync), sinon pas de résultat dispo immédiatement
    results = None
    if engine_name == "lesosai_stub":
        from app.services.thermique.lesosai_stub import LesosaiStubEngine
        stub: LesosaiStubEngine = engine  # type: ignore
        r = await stub.compute(thermal_model)
        results = r.to_dict()

    # Génération justificatif via LLM
    system = get_prompt_ch("thermique_ch")

    results_section = ""
    if results:
        results_section = f"""
RÉSULTATS DU CALCUL ({results.get('engine_used', engine_name)}) :
- Qh (besoin chauffage) : {results.get('qh_mj_m2_an')} MJ/m²/an
- Qww (ECS) : {results.get('qww_mj_m2_an')} MJ/m²/an
- E (énergie primaire) : {results.get('e_mj_m2_an')} MJ/m²/an
- Qh limite indicatif : {results.get('qh_limite_mj_m2_an')} MJ/m²/an
- Conformité calcul interne : {results.get('compliant')}
- Warnings : {results.get('warnings', [])}

ATTENTION : Ces résultats proviennent du moteur {results.get('engine_used')}.
Pour un justificatif OFFICIEL, le calcul doit être fait et validé dans Lesosai.
"""
    else:
        results_section = f"""
RÉSULTATS : pas encore calculés. Ce justificatif est une BASE de saisie à compléter par l'ingénieur après calcul dans Lesosai.
Mode engine : {engine_name}
"""

    user_content = f"""Rédiger un justificatif thermique SIA 380/1.

PROJET :
- Nom : {project_name or thermal_model.get('name', 'Projet')}
- Adresse : {project_address}
- Canton : {canton}
- Affectation : {thermal_model.get('affectation', '?')}
- Opération : {thermal_model.get('operation_type', 'neuf')}
- Standard visé : {thermal_model.get('standard', 'sia_380_1')}
- SRE : {prepared.get('sre_total_m2', 0):.1f} m²
- Station climatique : {thermal_model['climate'].get('station')}

ENVELOPPE :
- Zones : {len(thermal_model.get('zones', []))}
- Parois opaques : {len(thermal_model.get('walls', []))}
- Ouvertures : {len(thermal_model.get('openings', []))}
- Ponts thermiques : {len(thermal_model.get('thermal_bridges', []))}

HYPOTHÈSES FOURNIES :
{thermal_model.get('hypotheses') or 'Valeurs par défaut SIA 380/1'}

{results_section}

Rédiger le justificatif complet en markdown."""

    llm_result = await call_llm(
        task_type="calcul_thermique_re2020",  # routage Opus pour la fiabilité
        system_prompt=system,
        user_content=user_content,
        max_tokens=6000,
        temperature=0.1,
    )

    md = llm_result["text"]

    body_html = markdown_to_html(md)
    body_html += render_visa_block(author=author, role="Thermicien")

    pdf_bytes = render_pdf_from_html(
        body_html=body_html,
        title="Justificatif SIA 380/1",
        subtitle=f"Canton {canton} - {thermal_model.get('affectation', '')}",
        project_name=project_name or thermal_model.get('name', ''),
        project_address=project_address,
        author=author,
        reference=f"SIA380-1-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    return {
        "justificatif_md": md,
        "pdf_bytes": pdf_bytes,
        "results": results,
        "warnings": warnings,
        "engine_used": engine_name,
        "prepared": prepared,
        "llm": {
            "model": llm_result["model"],
            "tokens": llm_result["tokens_used"],
            "cost_eur": llm_result["cost_eur"],
        },
    }
