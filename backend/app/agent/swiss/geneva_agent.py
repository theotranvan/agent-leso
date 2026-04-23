"""Agent contrôle réglementaire Genève."""
import json
import logging
from datetime import datetime

from app.agent.router import call_llm
from app.agent.swiss.prompts_ch import get_prompt_ch
from app.ch.cantons.autres_romands import checklist_for_canton
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


async def run_geneva_control(project_data: dict, project_name: str = "", author: str = "") -> dict:
    """Produit le rapport de contrôle réglementaire genevois.

    project_data attendu : {affectation, operation_type, sre_m2, nb_logements, address, ...}
    """
    # Checklist générée par le code (déterministe)
    canton = project_data.get("canton", "GE")
    checklist = checklist_for_canton(canton, project_data)

    system = get_prompt_ch("controle_geneve")

    user_content = f"""Produire un rapport de contrôle réglementaire pré-dépôt pour Genève.

PROJET :
- Nom : {project_name}
- Adresse : {project_data.get('address', '')}
- Affectation : {project_data.get('affectation', '?')}
- Opération : {project_data.get('operation_type', '?')}
- SRE : {project_data.get('sre_m2', '?')} m²
- Nombre de logements : {project_data.get('nb_logements', '?')}
- Canton : {canton}

CHECKLIST GÉNÉRÉE PAR LE MOTEUR INTERNE (base déterministe) :
{json.dumps(checklist, ensure_ascii=False, indent=2)}

Transformer cette checklist en RAPPORT PROFESSIONNEL en markdown :
- Page de garde textuelle
- Synthèse (nombre de points BLOQUANT, IMPORTANT, etc.)
- Tableau par thème
- Pour chaque point : référence, statut, commentaire contextuel
- Conclusion avec actions à mener avant dépôt
- Note sur la responsabilité ingénieur/architecte"""

    llm_result = await call_llm(
        task_type="coordination_inter_lots",  # Sonnet pour raisonnement structuré
        system_prompt=system,
        user_content=user_content,
        max_tokens=4096,
        temperature=0.1,
    )

    md = llm_result["text"]
    body_html = markdown_to_html(md)
    pdf_bytes = render_pdf_from_html(
        body_html=body_html,
        title=f"Contrôle réglementaire pré-dépôt - {canton}",
        project_name=project_name,
        reference=f"CTRL-{canton}-{datetime.now().strftime('%Y%m%d')}",
    )

    return {
        "report_md": md,
        "pdf_bytes": pdf_bytes,
        "checklist": checklist,
        "llm": {
            "model": llm_result["model"],
            "tokens": llm_result["tokens_used"],
            "cost_eur": llm_result["cost_eur"],
        },
    }


async def execute(task: "dict[str, Any]") -> "dict[str, Any]":
    """Wrapper orchestrateur pour controle_reglementaire_geneve / vaud / canton."""
    from datetime import datetime
    from typing import Any
    from app.database import get_storage, get_supabase_admin

    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    project_data = params.get("project_data") or {}
    if not project_data:
        raise ValueError("project_data manquant (canton, affectation, sre_m2...)")

    project_name = params.get("project_name", "")
    author = params.get("author", "")

    pipeline = await run_geneva_control(project_data, project_name, author)

    pdf_bytes = pipeline["pdf_bytes"]
    canton = project_data.get("canton", "CH")
    storage = get_storage()
    filename = f"controle_{canton}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/controle/{task['id']}/{filename}"
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

    llm = pipeline.get("llm") or {}
    return {
        "result_url": signed_url,
        "preview": pipeline["report_md"][:500],
        "model": llm.get("model"),
        "tokens_used": llm.get("tokens", 0),
        "cost_eur": llm.get("cost_eur", 0),
        "email_bytes": pdf_bytes,
        "email_filename": filename,
    }
