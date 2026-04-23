"""Agent structure CH - pilote SAF + double-check + note SIA 260-267."""
import logging
from datetime import datetime
from typing import Any

from app.agent.router import call_llm
from app.agent.swiss.prompts_ch import get_prompt_ch
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html, render_visa_block
from app.services.structure.double_check import double_check
from app.services.structure.saf_generator import generate_saf_xlsx
from app.services.structure.saf_parser import parse_saf_results

logger = logging.getLogger(__name__)


def build_saf_and_sheet(structural_model: dict) -> dict:
    """Étape 1 : génère le fichier SAF à transmettre à l'ingénieur."""
    xlsx = generate_saf_xlsx(structural_model)
    return {
        "saf_xlsx": xlsx,
        "notice_md": _build_engineer_notice(structural_model),
    }


def _build_engineer_notice(model: dict) -> str:
    """Notice markdown expliquant à l'ingénieur ce qu'il doit faire avec le SAF."""
    lines = [
        "# Notice pour l'ingénieur structure",
        "",
        f"**Projet** : {model.get('project', {}).get('name', 'Projet')}",
        f"**Référentiel** : {model.get('project', {}).get('referentiel', 'sia').upper()}",
        "",
        "## Procédure",
        "",
        "1. Ouvrir le fichier SAF (.xlsx) dans votre logiciel de calcul (Scia Engineer, RFEM/RSTAB, etc.) via `File → Import → SAF`.",
        "2. Vérifier le modèle importé : géométrie, sections, matériaux, cas de charges.",
        "3. **Valider ou corriger** toute incohérence avant de lancer le calcul.",
        "4. Lancer le calcul dans votre logiciel.",
        "5. Exporter les résultats en SAF enrichi (Export → SAF avec résultats).",
        "6. Réimporter ce SAF enrichi dans BET Agent pour obtenir :",
        "   - Double-check analytique automatique (détection d'écart > 15%)",
        "   - Note de calcul SIA 260-267 pré-rédigée",
        "   - Bloc visa pour signature",
        "",
        "## Responsabilité",
        "",
        "Le calcul et la vérification engagent votre responsabilité d'ingénieur structure.",
        "L'agent BET produit des livrables préparatoires - il ne remplace pas votre vérification.",
        "",
        "## Cas de charges définis",
        "",
    ]
    for lc in model.get("load_cases", []):
        lines.append(f"- **{lc.get('id')}** : {lc.get('name')} ({lc.get('category', 'Variable')})")
    lines.append("")
    lines.append("## Combinaisons")
    lines.append("")
    for c in model.get("combinations", []):
        lines.append(f"- **{c.get('id')}** : {c.get('name')}")

    return "\n".join(lines)


async def run_structure_note_pipeline(
    structural_model: dict,
    saf_results_bytes: bytes,
    project_name: str = "",
    project_address: str = "",
    author: str = "",
) -> dict:
    """Étape 2 : une fois l'ingénieur a renvoyé le SAF enrichi avec résultats,
    on parse, on double-check, on génère la note SIA 260-267.
    """
    # Parsing
    results_parsed = parse_saf_results(saf_results_bytes)

    # Double-check
    dc = double_check(structural_model, results_parsed)

    # Synthèse pour le LLM
    system = get_prompt_ch("structure_ch")

    utilizations = results_parsed.get("utilizations", [])
    max_util = results_parsed.get("max_utilization", 0)

    user_content = f"""Rédiger la note de calcul structure SIA 260-267 pour ce projet.

PROJET :
- Nom : {project_name or structural_model.get('project', {}).get('name', 'Projet')}
- Adresse : {project_address}
- Référentiel : SIA 260-267
- Classe d'exposition : {structural_model.get('project', {}).get('exposure_class', 'XC2')}
- Classe de conséquence : {structural_model.get('project', {}).get('consequence_class', 'CC2')}
- Zone sismique SIA 261 : {structural_model.get('project', {}).get('seismic_zone', 'Z1b')}

MODÈLE STRUCTUREL
- Nombre de nœuds : {len(structural_model.get('nodes', []))}
- Nombre d'éléments 1D : {len(structural_model.get('members', []))}
- Nombre d'appuis : {len(structural_model.get('supports', []))}
- Cas de charges : {len(structural_model.get('load_cases', []))}
- Combinaisons : {len(structural_model.get('combinations', []))}

RÉSULTATS LOGICIEL (SAF importé)
- Feuilles disponibles : {results_parsed.get('sheets_found', [])}
- Taux de travail max : {max_util:.2f}
- Nombre de vérifications : {len(utilizations)}
- Warnings parsing : {results_parsed.get('warnings', [])}

DOUBLE-CHECK ANALYTIQUE INTERNE
- Résumé : {dc.get('summary')}
- Divergence max : {dc.get('max_divergence_pct', 0)}%
- Alertes : {dc.get('alerts_count', 0)}
- Détails des checks :
{_format_dc_checks(dc.get('checks', []))}

Rédiger la note complète avec toutes les sections requises. Inclure explicitement une section "Double-check analytique" rapportant les vérifications effectuées et les divergences. Ne déclarer conformité que si max_util < 1.0 ET aucune alerte critique sur le double-check."""

    llm_result = await call_llm(
        task_type="note_calcul_structure",
        system_prompt=system,
        user_content=user_content,
        max_tokens=8000,
        temperature=0.1,
    )

    md = llm_result["text"]
    body_html = markdown_to_html(md)
    body_html += render_visa_block(author=author, role="Ingénieur structure")

    pdf_bytes = render_pdf_from_html(
        body_html=body_html,
        title="Note de calcul structure SIA 260-267",
        project_name=project_name,
        project_address=project_address,
        author=author,
        reference=f"NC-STR-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    return {
        "note_md": md,
        "pdf_bytes": pdf_bytes,
        "results_parsed": results_parsed,
        "double_check": dc,
        "max_utilization": max_util,
        "compliant": max_util < 1.0 and dc.get("alerts_count", 0) == 0,
        "llm": {
            "model": llm_result["model"],
            "tokens": llm_result["tokens_used"],
            "cost_eur": llm_result["cost_eur"],
        },
    }


def _format_dc_checks(checks: list[dict], limit: int = 20) -> str:
    lines = []
    for c in checks[:limit]:
        lines.append(
            f"  - [{c.get('status')}] {c.get('member_id')} / {c.get('check_type')}: "
            f"analytique={c.get('analytical_value')} {c.get('analytical_unit', '')} "
            f"vs logiciel={c.get('software_value')} "
            f"→ divergence {c.get('divergence_pct')}%"
        )
    if len(checks) > limit:
        lines.append(f"  ... et {len(checks) - limit} autres vérifications")
    return "\n".join(lines)


async def execute(task: "dict[str, Any]") -> "dict[str, Any]":
    """Wrapper orchestrateur pour note_calcul_sia_260_267.

    Deux modes selon les input_params :
      - step='build_saf' (défaut) : génère le SAF + notice ingénieur (étape 1)
      - step='generate_note' : parse le SAF enrichi + produit la note SIA 260-267 (étape 2)

    Input params :
      - structural_model: dict (nodes, members, supports, loads, project_info)
      - step: 'build_saf' | 'generate_note'
      - saf_results_storage_path: str (requis si step='generate_note')
      - project_name, project_address, author, engineer_validated
    """
    import base64
    from datetime import datetime
    from typing import Any
    from app.database import get_storage, get_supabase_admin
    from app.services.pdf_generator import markdown_to_html, render_pdf_from_html, render_visa_block

    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    structural_model = params.get("structural_model") or {}
    if not structural_model:
        raise ValueError("structural_model manquant")

    step = params.get("step", "build_saf")
    project_name = params.get("project_name", "")

    storage = get_storage()
    admin = get_supabase_admin()

    if step == "build_saf":
        # Étape 1 — génération SAF à transmettre à l'ingénieur
        artifacts = build_saf_and_sheet(structural_model)
        filename = f"SAF_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        path = f"{org_id}/structure/{task['id']}/{filename}"
        storage.upload(
            path, artifacts["saf_xlsx"],
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        signed_url = storage.get_signed_url(path, expires_in=604800)

        # Notice PDF
        notice_pdf = render_pdf_from_html(
            body_html=markdown_to_html(artifacts["notice_md"]),
            title="Notice structure — SAF à traiter",
            project_name=project_name,
            reference=f"STRUCT-SAF-{datetime.now().strftime('%Y%m%d-%H%M')}",
        )
        notice_filename = filename.replace(".xlsx", "_notice.pdf")
        notice_path = f"{org_id}/structure/{task['id']}/{notice_filename}"
        storage.upload(notice_path, notice_pdf, content_type="application/pdf")

        admin.table("documents").insert({
            "organization_id": org_id,
            "project_id": project_id,
            "filename": filename,
            "file_type": "xlsx",
            "storage_path": path,
            "processed": True,
        }).execute()

        return {
            "result_url": signed_url,
            "preview": artifacts["notice_md"][:500],
            "email_bytes": artifacts["saf_xlsx"],
            "email_filename": filename,
        }

    if step == "generate_note":
        # Étape 2 — l'ingénieur doit avoir coché engineer_validated
        if not params.get("engineer_validated"):
            raise ValueError(
                "engineer_validated=True requis pour générer la note "
                "(l'ingénieur structure doit avoir validé les résultats)"
            )

        saf_path = params.get("saf_results_storage_path")
        if not saf_path:
            raise ValueError("saf_results_storage_path manquant")

        saf_bytes = storage.download(saf_path)

        pipeline = await run_structure_note_pipeline(
            structural_model=structural_model,
            saf_results_bytes=saf_bytes,
            project_name=project_name,
            project_address=params.get("project_address", ""),
            author=params.get("author", ""),
        )

        pdf_bytes = pipeline["pdf_bytes"]
        filename = f"note_SIA_260_267_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path = f"{org_id}/structure/{task['id']}/{filename}"
        storage.upload(path, pdf_bytes, content_type="application/pdf")
        signed_url = storage.get_signed_url(path, expires_in=604800)

        admin.table("documents").insert({
            "organization_id": org_id,
            "project_id": project_id,
            "filename": filename,
            "file_type": "pdf",
            "storage_path": path,
            "processed": True,
        }).execute()

        llm = pipeline.get("llm") or {}
        return {
            "result_url": signed_url,
            "preview": pipeline["note_md"][:500],
            "model": llm.get("model"),
            "tokens_used": llm.get("tokens", 0),
            "cost_eur": llm.get("cost_eur", 0),
            "email_bytes": pdf_bytes,
            "email_filename": filename,
        }

    raise ValueError(f"step inconnu: {step}")
