"""Module Rapport - CR réunion, mémoire technique, résumé, veille réglementaire."""
import json
import logging
from datetime import datetime
from typing import Any

from app.agent.prompts import get_system_prompt
from app.agent.rag import build_project_context, get_project_summary
from app.agent.router import call_llm
from app.database import get_storage, get_supabase_admin
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Route vers le bon type de rapport."""
    task_type = task["task_type"]
    if task_type == "compte_rendu_reunion":
        return await _compte_rendu(task)
    elif task_type == "memoire_technique":
        return await _memoire_technique(task)
    elif task_type == "resume_document":
        return await _resume_document(task)
    else:
        return await execute_generic(task)


async def execute_generic(task: dict[str, Any]) -> dict[str, Any]:
    """Tâche LLM générique qui retourne du texte (veille, alerte, metadata)."""
    params = task.get("input_params") or {}
    task_type = task["task_type"]
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    content = params.get("content", "")
    rag_context = ""
    if project_id:
        rag_context = await build_project_context(content[:500] or task_type, org_id, project_id, top_k=4)

    user_content = f"{content}\n\n{rag_context}" if rag_context else content

    llm_result = await call_llm(
        task_type=task_type,
        system_prompt=get_system_prompt(task_type),
        user_content=user_content or f"Exécute la tâche {task_type} selon les instructions système.",
        max_tokens=4096,
        temperature=0.3,
    )

    return {
        "result_url": None,
        "preview": llm_result["text"][:1000],
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
    }


async def _compte_rendu(task: dict[str, Any]) -> dict[str, Any]:
    """Compte-rendu de réunion."""
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    project_info = await get_project_summary(org_id, project_id) if project_id else {}
    project_name = project_info.get("name") or params.get("project_name", "")

    notes = params.get("notes", "") or params.get("transcription", "")
    participants = params.get("participants", [])
    date_reunion = params.get("date", datetime.now().strftime("%d/%m/%Y"))
    objet = params.get("objet", "Réunion de projet")
    lieu = params.get("lieu", "")

    participants_str = "\n".join(f"- {p}" for p in participants) if participants else "Non précisés"

    user_content = f"""Rédiger un compte-rendu professionnel de la réunion suivante.

**Objet :** {objet}
**Date :** {date_reunion}
**Lieu :** {lieu}
**Projet :** {project_name}
**Participants :**
{participants_str}

**Notes brutes / transcription :**
{notes}

Produire le CR complet en markdown avec toutes les sections standard (objet, participants, ODJ, synthèse, décisions, tableau des actions, prochaine réunion)."""

    llm_result = await call_llm(
        task_type="compte_rendu_reunion",
        system_prompt=get_system_prompt("compte_rendu_reunion"),
        user_content=user_content,
        max_tokens=4096,
        temperature=0.2,
    )

    cr_md = llm_result["text"]
    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(cr_md),
        title="Compte-rendu de réunion",
        subtitle=objet,
        project_name=project_name,
        author=params.get("author", ""),
        reference=f"CR-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    storage = get_storage()
    filename = f"CR_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/comptes_rendus/{task['id']}/{filename}"
    storage.upload(path, pdf_bytes, content_type="application/pdf")
    signed_url = storage.get_signed_url(path, expires_in=604800)

    get_supabase_admin().table("documents").insert({
        "organization_id": org_id,
        "project_id": project_id,
        "filename": filename,
        "file_type": "pdf",
        "storage_path": path,
        "processed": True,
    }).execute()

    # Ajout destinataires automatiques : participants
    if participants and not (params.get("recipient_emails")):
        # On ne peut pas inférer les emails depuis juste les noms, donc on laisse vide
        pass

    return {
        "result_url": signed_url,
        "preview": cr_md[:500],
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
    }


async def _memoire_technique(task: dict[str, Any]) -> dict[str, Any]:
    """Mémoire technique pour appel d'offres."""
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    project_info = await get_project_summary(org_id, project_id) if project_id else {}
    project_name = project_info.get("name") or params.get("project_name", "")

    brief = params.get("brief", "")
    rag_context = await build_project_context(
        brief or "mémoire technique méthodologie moyens",
        org_id, project_id, top_k=6,
    )

    user_content = f"""Rédiger un mémoire technique pour la réponse à l'appel d'offres suivant.

**Projet :** {project_name}
**Brief / CCTP client :**
{brief}

{rag_context}

Produire le mémoire technique complet en markdown, convaincant et argumenté, adapté au projet."""

    llm_result = await call_llm(
        task_type="memoire_technique",
        system_prompt=get_system_prompt("memoire_technique"),
        user_content=user_content,
        max_tokens=6000,
        temperature=0.3,
    )

    md = llm_result["text"]
    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(md),
        title="Mémoire Technique",
        subtitle="Réponse à appel d'offres",
        project_name=project_name,
        author=params.get("author", ""),
        reference=f"MT-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    storage = get_storage()
    filename = f"MemoireTech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/memoires/{task['id']}/{filename}"
    storage.upload(path, pdf_bytes, content_type="application/pdf")
    signed_url = storage.get_signed_url(path, expires_in=604800)

    get_supabase_admin().table("documents").insert({
        "organization_id": org_id,
        "project_id": project_id,
        "filename": filename,
        "file_type": "pdf",
        "storage_path": path,
        "processed": True,
    }).execute()

    return {
        "result_url": signed_url,
        "preview": md[:500],
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
    }


async def _resume_document(task: dict[str, Any]) -> dict[str, Any]:
    """Résumé d'un document existant."""
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    document_id = params.get("document_id")
    doc_text = ""
    filename_source = ""

    if document_id:
        admin = get_supabase_admin()
        doc = admin.table("documents").select("*").eq("id", document_id).maybe_single().execute()
        if doc.data:
            filename_source = doc.data["filename"]
            doc_text = doc.data.get("extracted_text") or ""
            if not doc_text:
                # Re-extraction à la volée
                from app.services.pdf_extractor import extract_text_from_pdf
                try:
                    storage = get_storage()
                    pdf_bytes = storage.download(doc.data["storage_path"])
                    doc_text, _ = extract_text_from_pdf(pdf_bytes)
                except Exception as e:
                    logger.error(f"Erreur re-extraction document: {e}")

    doc_text = doc_text or params.get("content", "")
    if not doc_text:
        raise ValueError("Aucun contenu à résumer")

    llm_result = await call_llm(
        task_type="resume_document",
        system_prompt=get_system_prompt("resume_document"),
        user_content=f"Document à résumer :\n\n{doc_text[:30000]}",
        max_tokens=2048,
        temperature=0.2,
    )

    return {
        "result_url": None,
        "preview": llm_result["text"],
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
    }
