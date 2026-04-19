"""Module Coordination inter-lots - détection de conflits entre fichiers IFC."""
import logging
from datetime import datetime
from typing import Any

from app.agent.prompts import get_system_prompt
from app.agent.rag import get_project_summary
from app.agent.router import call_llm
from app.database import get_storage, get_supabase_admin
from app.services.ifc_parser import detect_clashes, generate_bcf_xml
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Détecte les conflits entre plusieurs fichiers IFC (1 par lot).

    input_params :
      - ifc_documents : [{"lot": "cvc", "document_id": "uuid"}, ...]
    """
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    project_info = await get_project_summary(org_id, project_id) if project_id else {}
    project_name = project_info.get("name") or params.get("project_name", "Projet")
    project_address = project_info.get("address") or ""

    ifc_docs = params.get("ifc_documents", [])
    if len(ifc_docs) < 2:
        raise ValueError("La coordination nécessite au moins 2 fichiers IFC (un par lot)")

    # Télécharge chaque IFC
    storage = get_storage()
    admin = get_supabase_admin()
    ifc_models: list[tuple[str, bytes]] = []
    for entry in ifc_docs:
        doc = admin.table("documents").select("*").eq("id", entry["document_id"]).maybe_single().execute()
        if not doc.data:
            logger.warning(f"Document IFC {entry['document_id']} introuvable")
            continue
        try:
            ifc_bytes = storage.download(doc.data["storage_path"])
            ifc_models.append((entry["lot"], ifc_bytes))
        except Exception as e:
            logger.error(f"Erreur téléchargement IFC {entry['document_id']}: {e}")

    if len(ifc_models) < 2:
        raise ValueError("Impossible de charger 2 fichiers IFC valides")

    # Détection clashes
    clashes = detect_clashes(ifc_models)
    logger.info(f"{len(clashes)} conflits détectés entre {len(ifc_models)} lots")

    # Analyse par LLM pour priorisation + plan d'action
    clashes_summary = _format_clashes_for_llm(clashes)
    system_prompt = get_system_prompt("coordination_inter_lots")

    user_content = f"""Analyser les {len(clashes)} conflits géométriques détectés entre lots du projet **{project_name}**.

**Lots analysés :** {', '.join(m[0] for m in ifc_models)}

**Liste brute des conflits détectés (par bounding box) :**
{clashes_summary}

Produire un rapport de coordination structuré en markdown, avec :
1. Synthèse (nb conflits, criticité, lots impactés)
2. Matrice conflits par couple de lots
3. Liste détaillée des top 30 conflits les plus critiques avec analyse et résolution proposée
4. Plan d'action

Sois concret et actionnable."""

    llm_result = await call_llm(
        task_type="coordination_inter_lots",
        system_prompt=system_prompt,
        user_content=user_content,
        max_tokens=8000,
        temperature=0.2,
    )

    rapport_md = llm_result["text"]
    body_html = markdown_to_html(rapport_md)

    # Génération PDF rapport
    pdf_bytes = render_pdf_from_html(
        body_html=body_html,
        title="Rapport de Coordination inter-lots",
        subtitle=f"{len(clashes)} conflits détectés",
        project_name=project_name,
        project_address=project_address,
        author=params.get("author", ""),
        reference=f"COORD-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    # Génération BCF XML standard
    bcf_xml = generate_bcf_xml(clashes, project_name=project_name)

    # Upload
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"Coordination_{ts}.pdf"
    bcf_filename = f"Coordination_{ts}.bcf.xml"
    pdf_path = f"{org_id}/coordination/{task['id']}/{pdf_filename}"
    bcf_path = f"{org_id}/coordination/{task['id']}/{bcf_filename}"

    storage.upload(pdf_path, pdf_bytes, content_type="application/pdf")
    storage.upload(bcf_path, bcf_xml.encode("utf-8"), content_type="application/xml")

    pdf_url = storage.get_signed_url(pdf_path, expires_in=604800)

    for fname, fpath, ftype in [(pdf_filename, pdf_path, "pdf"), (bcf_filename, bcf_path, "bcf")]:
        admin.table("documents").insert({
            "organization_id": org_id,
            "project_id": project_id,
            "filename": fname,
            "file_type": ftype,
            "storage_path": fpath,
            "processed": True,
        }).execute()

    return {
        "result_url": pdf_url,
        "preview": f"{len(clashes)} conflits détectés entre {len(ifc_models)} lots. Rapport PDF + BCF XML générés.\n\n" +
                   rapport_md[:400],
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": pdf_filename,
    }


def _format_clashes_for_llm(clashes: list[dict], max_items: int = 80) -> str:
    """Formate la liste des clashes pour le prompt LLM."""
    if not clashes:
        return "Aucun conflit détecté."

    lines = []
    for i, c in enumerate(clashes[:max_items], 1):
        a = c["element_a"]
        b = c["element_b"]
        lines.append(f"{i}. [{a['lot']}] {a['type']} '{a['name'][:40]}' ⟷ [{b['lot']}] {b['type']} '{b['name'][:40]}'")

    extra = ""
    if len(clashes) > max_items:
        extra = f"\n...et {len(clashes) - max_items} autres conflits."

    return "\n".join(lines) + extra
