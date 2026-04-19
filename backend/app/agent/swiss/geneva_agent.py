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
