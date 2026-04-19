"""Module CCTP - Cahier des Clauses Techniques Particulières."""
import logging
import uuid
from datetime import datetime
from typing import Any

from app.agent.prompts import get_normes_for_lot, get_system_prompt
from app.agent.rag import build_project_context, get_project_summary
from app.agent.router import call_llm
from app.database import get_storage, get_supabase_admin
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Exécute une tâche de rédaction CCTP."""
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    lot = params.get("lot", "electricite")
    type_ouvrage = params.get("type_ouvrage", "")
    niveau = params.get("niveau_prestation", "standard")
    surface = params.get("surface", "")
    contraintes = params.get("contraintes", "")

    project_info = await get_project_summary(org_id, project_id) if project_id else {}
    project_name = project_info.get("name") or params.get("project_name", "Projet")
    project_address = project_info.get("address") or ""

    context_query = f"CCTP lot {lot} {type_ouvrage} {contraintes}"
    rag_context = await build_project_context(context_query, org_id, project_id, top_k=6)

    normes = get_normes_for_lot(lot)
    normes_str = "\n".join(f"- {n}" for n in normes)

    user_content = f"""Rédiger un CCTP complet pour le lot suivant :

**Projet :** {project_name}
**Adresse :** {project_address}
**Type d'ouvrage :** {type_ouvrage}
**Lot :** {lot.upper()}
**Niveau de prestation :** {niveau}
**Surface :** {surface} m²

**Contraintes particulières :**
{contraintes or "Aucune contrainte particulière signalée."}

**Normes applicables au lot (à citer explicitement dans le CCTP) :**
{normes_str or "À identifier selon le lot."}

{rag_context}

Produire le CCTP complet en markdown, structuré, prescriptif. Minimum 1500 mots. Inclure toutes les sections habituelles d'un CCTP professionnel."""

    system_prompt = get_system_prompt("redaction_cctp")

    llm_result = await call_llm(
        task_type="redaction_cctp",
        system_prompt=system_prompt,
        user_content=user_content,
        max_tokens=8000,
        temperature=0.2,
    )

    cctp_markdown = llm_result["text"]
    body_html = markdown_to_html(cctp_markdown)
    reference = f"CCTP-{lot.upper()[:4]}-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6]}"

    pdf_bytes = render_pdf_from_html(
        body_html=body_html,
        title=f"CCTP — Lot {lot.upper()}",
        subtitle=f"Niveau : {niveau}",
        project_name=project_name,
        project_address=project_address,
        lot=lot.upper(),
        author=params.get("author", ""),
        reference=reference,
    )

    storage = get_storage()
    filename = f"CCTP_{lot}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/cctp/{task['id']}/{filename}"
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
        "preview": cctp_markdown[:500] + "..." if len(cctp_markdown) > 500 else cctp_markdown,
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
    }
