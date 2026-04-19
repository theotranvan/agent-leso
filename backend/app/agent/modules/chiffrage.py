"""Module Chiffrage - DPGF et DQE depuis métrés PDF."""
import json
import logging
from datetime import datetime
from typing import Any

from app.agent.prompts import get_system_prompt
from app.agent.rag import build_project_context, get_project_summary
from app.agent.router import call_llm
from app.database import get_storage, get_supabase_admin
from app.services.excel_generator import generate_dpgf_excel, generate_dqe_excel
from app.services.pdf_extractor import extract_tables_from_pdf, extract_text_from_pdf
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Exécute un chiffrage DPGF ou DQE."""
    params = task.get("input_params") or {}
    task_type = task["task_type"]
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    project_info = await get_project_summary(org_id, project_id) if project_id else {}
    project_name = project_info.get("name") or params.get("project_name", "Projet")
    org = get_supabase_admin().table("organizations").select("name").eq("id", org_id).maybe_single().execute()
    org_name = org.data.get("name", "") if org.data else ""

    # Récup métré source
    metre_text = ""
    if params.get("metre_document_id"):
        metre_text = await _get_metre_content(params["metre_document_id"])
    elif params.get("metre_text"):
        metre_text = params["metre_text"]

    rag_context = await build_project_context(
        f"métré chiffrage {task_type} {params.get('lot', '')}",
        org_id, project_id, top_k=4,
    )

    if task_type == "chiffrage_dpgf":
        return await _generate_dpgf(task, params, project_name, org_name, metre_text, rag_context)
    else:
        return await _generate_dqe(task, params, project_name, org_name, metre_text, rag_context)


async def _generate_dpgf(task, params, project_name, org_name, metre_text, rag_context) -> dict[str, Any]:
    lot = params.get("lot", "")
    system_prompt = get_system_prompt("chiffrage_dpgf")

    user_content = f"""Générer le DPGF pour ce projet.

**Projet :** {project_name}
**Lot :** {lot}

**Métré / descriptif fourni :**
{metre_text[:15000] if metre_text else "Aucun métré fourni — poser les hypothèses nécessaires."}

{rag_context}

Retourner uniquement le JSON strict demandé par les instructions système."""

    llm_result = await call_llm(
        task_type="chiffrage_dpgf",
        system_prompt=system_prompt,
        user_content=user_content,
        max_tokens=8000,
        temperature=0.1,
    )

    data = _parse_json_lenient(llm_result["text"])
    lines = data.get("lines", [])

    excel_bytes = generate_dpgf_excel(
        project_name=project_name,
        lot=lot,
        lines=lines,
        organization_name=org_name,
    )

    # PDF récapitulatif
    total_ht = sum((l.get("quantite") or 0) * (l.get("prix_unitaire") or 0) for l in lines if not l.get("is_section"))
    recap_md = f"""# Récapitulatif DPGF — Lot {lot}

**Projet :** {project_name}
**Nombre d'articles :** {len([l for l in lines if not l.get('is_section')])}
**Montant total HT estimé :** {total_ht:,.2f} €

## Détail par article

| N° | Désignation | Unité | Quantité | PU HT | Total HT |
|----|-------------|-------|----------|-------|----------|
""" + "\n".join(
        f"| {l.get('article', '')} | {l.get('designation', '')[:80]} | {l.get('unite', '')} | {l.get('quantite', '')} | {l.get('prix_unitaire', '')} € | {((l.get('quantite') or 0) * (l.get('prix_unitaire') or 0)):.2f} € |"
        for l in lines[:80] if not l.get("is_section")
    )

    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(recap_md),
        title=f"DPGF — Lot {lot}",
        subtitle=f"Montant total HT : {total_ht:,.2f} €",
        project_name=project_name,
        lot=lot,
        reference=f"DPGF-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    storage = get_storage()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"DPGF_{lot}_{ts}.xlsx"
    pdf_filename = f"DPGF_{lot}_recap_{ts}.pdf"
    excel_path = f"{task['organization_id']}/chiffrage/{task['id']}/{excel_filename}"
    pdf_path = f"{task['organization_id']}/chiffrage/{task['id']}/{pdf_filename}"

    storage.upload(excel_path, excel_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    storage.upload(pdf_path, pdf_bytes, content_type="application/pdf")

    excel_url = storage.get_signed_url(excel_path, expires_in=604800)
    pdf_url = storage.get_signed_url(pdf_path, expires_in=604800)

    admin = get_supabase_admin()
    for fname, fpath, ftype in [(excel_filename, excel_path, "xlsx"), (pdf_filename, pdf_path, "pdf")]:
        admin.table("documents").insert({
            "organization_id": task["organization_id"],
            "project_id": task.get("project_id"),
            "filename": fname,
            "file_type": ftype,
            "storage_path": fpath,
            "processed": True,
        }).execute()

    return {
        "result_url": excel_url,
        "preview": f"DPGF généré — {len(lines)} articles — Total HT : {total_ht:,.2f} €\n\nFichiers : Excel (actif) + PDF récap",
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": excel_bytes,
        "email_filename": excel_filename,
    }


async def _generate_dqe(task, params, project_name, org_name, metre_text, rag_context) -> dict[str, Any]:
    lots_input = params.get("lots", [])
    if not lots_input:
        # Fallback : déduire les lots du métré
        lots_input = ["gros_oeuvre", "second_oeuvre", "cvc", "electricite", "plomberie"]

    system_prompt = get_system_prompt("chiffrage_dqe")
    user_content = f"""Générer le DQE multi-lots pour ce projet.

**Projet :** {project_name}
**Lots à chiffrer :** {', '.join(lots_input)}

**Métré / descriptif fourni :**
{metre_text[:15000] if metre_text else "Aucun métré fourni — poser les hypothèses."}

{rag_context}

Retourner un JSON :
{{
  "lots": {{
    "nom_lot_1": [ {{"article": "1.1", "designation": "...", "unite": "...", "quantite": X, "prix_unitaire": Y}}, ... ],
    ...
  }}
}}
Aucun autre texte."""

    llm_result = await call_llm(
        task_type="chiffrage_dqe",
        system_prompt=system_prompt,
        user_content=user_content,
        max_tokens=8000,
        temperature=0.1,
    )

    data = _parse_json_lenient(llm_result["text"])
    lots_data = data.get("lots", {})
    if not lots_data:  # tolérance format
        lots_data = {lot: data.get(lot, []) for lot in lots_input if lot in data}

    excel_bytes = generate_dqe_excel(
        project_name=project_name,
        lots_data=lots_data,
        organization_name=org_name,
    )

    storage = get_storage()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"DQE_{project_name.replace(' ', '_')[:30]}_{ts}.xlsx"
    path = f"{task['organization_id']}/chiffrage/{task['id']}/{filename}"
    storage.upload(path, excel_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    signed_url = storage.get_signed_url(path, expires_in=604800)

    total = sum(
        sum((l.get("quantite") or 0) * (l.get("prix_unitaire") or 0) for l in lines)
        for lines in lots_data.values()
    )

    admin = get_supabase_admin()
    admin.table("documents").insert({
        "organization_id": task["organization_id"],
        "project_id": task.get("project_id"),
        "filename": filename,
        "file_type": "xlsx",
        "storage_path": path,
        "processed": True,
    }).execute()

    return {
        "result_url": signed_url,
        "preview": f"DQE généré — {len(lots_data)} lots — Total HT : {total:,.2f} €",
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": excel_bytes,
        "email_filename": filename,
    }


async def _get_metre_content(document_id: str) -> str:
    """Récupère le texte et les tableaux d'un document métré PDF."""
    admin = get_supabase_admin()
    doc = admin.table("documents").select("*").eq("id", document_id).maybe_single().execute()
    if not doc.data:
        return ""

    # Si le texte est déjà extrait
    if doc.data.get("extracted_text"):
        text = doc.data["extracted_text"]
    else:
        storage = get_storage()
        try:
            pdf_bytes = storage.download(doc.data["storage_path"])
            text, _ = extract_text_from_pdf(pdf_bytes)
        except Exception as e:
            logger.error(f"Erreur lecture métré: {e}")
            return ""

    # Ajoute les tableaux si c'est un PDF
    if doc.data.get("file_type") == "pdf":
        try:
            storage = get_storage()
            pdf_bytes = storage.download(doc.data["storage_path"])
            tables = extract_tables_from_pdf(pdf_bytes)
            if tables:
                text += "\n\n=== TABLEAUX EXTRAITS ===\n"
                for i, tbl in enumerate(tables[:20]):
                    text += f"\nTableau {i + 1}:\n"
                    for row in tbl:
                        text += " | ".join(str(c) for c in row) + "\n"
        except Exception:
            pass

    return text


def _parse_json_lenient(text: str) -> dict:
    """Parse JSON en tolérant les blocs markdown ```json``` et le texte autour."""
    text = text.strip()
    # Retire les balises markdown
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    # Cherche le premier { et le dernier }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        logger.error(f"Parse JSON échoué: {e}")
        return {}
