"""Module DOE - Compilation du Dossier d'Ouvrages Exécutés."""
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
    """Compile un DOE à partir des documents du projet + input utilisateur."""
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    project_info = await get_project_summary(org_id, project_id) if project_id else {}
    project_name = project_info.get("name") or params.get("project_name", "Projet")
    project_address = project_info.get("address") or ""

    lots = params.get("lots", project_info.get("lots", []))
    intervenants = params.get("intervenants", [])
    date_reception = params.get("date_reception", "")

    # RAG large pour récupérer les infos techniques des documents projet
    rag_context = await build_project_context(
        "DOE réception ouvrages fiches produits notices maintenance garanties",
        org_id, project_id, top_k=10, max_chars=12000,
    )

    # Liste des documents du projet
    admin = get_supabase_admin()
    docs = admin.table("documents").select("filename,file_type").eq("organization_id", org_id).eq("project_id", project_id).limit(200).execute()
    docs_list = "\n".join(f"- {d['filename']} ({d['file_type']})" for d in (docs.data or []))

    intervenants_str = "\n".join(f"- {i}" for i in intervenants) if intervenants else "À compléter"
    lots_str = "\n".join(f"- {l}" for l in lots) if lots else "À identifier"

    user_content = f"""Compiler un DOE (Dossier d'Ouvrages Exécutés) complet pour le projet suivant.

**Projet :** {project_name}
**Adresse :** {project_address}
**Date de réception :** {date_reception or "Non précisée"}

**Lots réalisés :**
{lots_str}

**Intervenants :**
{intervenants_str}

**Documents disponibles au projet ({len(docs.data or [])}) :**
{docs_list[:3000]}

{rag_context}

Produire le DOE complet en markdown avec toutes les sections habituelles. Organiser clairement les ouvrages par lot, citer les documents de référence, et lister les garanties applicables (décennale, biennale, parfait achèvement)."""

    llm_result = await call_llm(
        task_type="doe_compilation",
        system_prompt=get_system_prompt("doe_compilation"),
        user_content=user_content,
        max_tokens=8000,
        temperature=0.2,
    )

    doe_md = llm_result["text"]
    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(doe_md),
        title="DOE — Dossier d'Ouvrages Exécutés",
        subtitle=f"Réception : {date_reception or 'À confirmer'}",
        project_name=project_name,
        project_address=project_address,
        author=params.get("author", ""),
        reference=f"DOE-{datetime.now().strftime('%Y%m%d')}",
    )

    storage = get_storage()
    filename = f"DOE_{project_name.replace(' ', '_')[:30]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/doe/{task['id']}/{filename}"
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

    return {
        "result_url": signed_url,
        "preview": doe_md[:500],
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
    }
