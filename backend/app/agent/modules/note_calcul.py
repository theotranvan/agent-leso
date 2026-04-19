"""Module Note de calcul - Structure (Eurocodes), Thermique RE2020, Acoustique."""
import logging
import uuid
from datetime import datetime
from typing import Any

from app.agent.prompts import get_system_prompt
from app.agent.rag import build_project_context, get_project_summary
from app.agent.router import call_llm
from app.database import get_storage, get_supabase_admin
from app.services.ifc_parser import (
    extract_spaces_and_surfaces,
    extract_structural_elements,
    extract_thermal_properties,
    parse_ifc_metadata,
)
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html, render_visa_block

logger = logging.getLogger(__name__)


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Exécute une note de calcul (structure / thermique / acoustique / vérif Eurocode)."""
    params = task.get("input_params") or {}
    task_type = task["task_type"]
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    project_info = await get_project_summary(org_id, project_id) if project_id else {}
    project_name = project_info.get("name") or params.get("project_name", "Projet")
    project_address = project_info.get("address") or ""

    # Extraction données IFC si présent
    ifc_data_str = ""
    if params.get("ifc_document_id"):
        ifc_data_str = await _extract_ifc_data(params["ifc_document_id"], task_type)

    # RAG contexte
    domain_query = {
        "note_calcul_structure": "structure dimensionnement charges Eurocode béton acier",
        "verification_eurocode": "vérification Eurocode charges combinaisons",
        "calcul_thermique_re2020": "thermique RE2020 enveloppe U-value isolation",
        "calcul_acoustique": "acoustique isolement NRA",
    }
    rag_context = await build_project_context(
        domain_query.get(task_type, task_type),
        org_id, project_id, top_k=6,
    )

    # Données complémentaires
    hypotheses = params.get("hypotheses", "")
    elements_a_calculer = params.get("elements", "")
    localisation = params.get("localisation", "France")  # pour choix EC vs SIA
    zone_climatique = params.get("zone_climatique", "")
    zone_sismique = params.get("zone_sismique", "")

    system_prompt = get_system_prompt(task_type)

    type_labels = {
        "note_calcul_structure": "Note de calcul structure",
        "verification_eurocode": "Vérification Eurocode",
        "calcul_thermique_re2020": "Calcul thermique RE2020",
        "calcul_acoustique": "Note de calcul acoustique",
    }
    doc_title = type_labels.get(task_type, "Note de calcul")

    user_content = f"""Produire une {doc_title.lower()} complète, rigoureuse et vérifiable.

**Projet :** {project_name}
**Adresse :** {project_address}
**Localisation :** {localisation}
{f"**Zone climatique :** {zone_climatique}" if zone_climatique else ""}
{f"**Zone sismique :** {zone_sismique}" if zone_sismique else ""}

**Éléments à calculer / vérifier :**
{elements_a_calculer or "Selon hypothèses fournies."}

**Hypothèses fournies :**
{hypotheses or "À définir sur la base des données IFC et du contexte projet."}

{ifc_data_str}

{rag_context}

Produire la note de calcul complète en markdown. Toutes les formules doivent être explicitées et les valeurs numériques calculées. Conclure explicitement sur la conformité de chaque vérification."""

    llm_result = await call_llm(
        task_type=task_type,
        system_prompt=system_prompt,
        user_content=user_content,
        max_tokens=8000,
        temperature=0.1,  # faible pour calculs
    )

    note_markdown = llm_result["text"]
    body_html = markdown_to_html(note_markdown)
    body_html += render_visa_block(author=params.get("author", ""), role="Ingénieur calculateur")

    reference = f"NC-{task_type[:8].upper()}-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6]}"

    pdf_bytes = render_pdf_from_html(
        body_html=body_html,
        title=doc_title,
        subtitle=f"Conforme aux {'Eurocodes' if 'structure' in task_type or 'eurocode' in task_type else 'RE2020' if 'thermique' in task_type else 'NRA'}",
        project_name=project_name,
        project_address=project_address,
        author=params.get("author", ""),
        reference=reference,
    )

    storage = get_storage()
    filename = f"{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/notes_calcul/{task['id']}/{filename}"
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
        "preview": note_markdown[:500] + "..." if len(note_markdown) > 500 else note_markdown,
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
    }


async def _extract_ifc_data(document_id: str, task_type: str) -> str:
    """Extrait et formate les données IFC pertinentes pour la note de calcul."""
    admin = get_supabase_admin()
    doc = admin.table("documents").select("*").eq("id", document_id).maybe_single().execute()
    if not doc.data:
        return ""

    storage = get_storage()
    try:
        ifc_bytes = storage.download(doc.data["storage_path"])
    except Exception as e:
        logger.error(f"Impossible de télécharger IFC: {e}")
        return ""

    metadata = parse_ifc_metadata(ifc_bytes)
    parts = [f"**DONNÉES EXTRAITES DU FICHIER IFC ({doc.data['filename']}) :**\n",
             f"- Schéma IFC : {metadata.get('schema')}",
             f"- Projet BIM : {metadata.get('project_name')}",
             f"- Bâtiment : {metadata.get('building_name')}",
             f"- Nombre d'étages : {metadata.get('nb_storeys')}",
             f"- Nombre d'espaces : {metadata.get('nb_spaces')}",
             ""]

    if "thermique" in task_type:
        thermal = extract_thermal_properties(ifc_bytes)
        if thermal:
            parts.append("**Propriétés thermiques des parois (extraites) :**")
            for elem in thermal[:30]:
                thermal_props = elem.get("thermal_properties", {})
                u_value = thermal_props.get("ThermalTransmittance") or thermal_props.get("U_Value")
                parts.append(f"- {elem['type']} '{elem['name']}' : U = {u_value}" +
                             (f", matériaux : {[m['name'] for m in elem.get('materials', [])]}" if elem.get('materials') else ""))
            parts.append("")

        spaces = extract_spaces_and_surfaces(ifc_bytes)
        if spaces:
            parts.append("**Espaces et surfaces :**")
            total_area = 0.0
            for sp in spaces[:50]:
                if sp.get("area"):
                    total_area += sp["area"]
                parts.append(f"- {sp.get('long_name') or sp.get('name')} : {sp.get('area', '?')} m², V = {sp.get('volume', '?')} m³")
            parts.append(f"**Surface totale plancher : {total_area:.2f} m²**")
            parts.append("")

    if "structure" in task_type or "eurocode" in task_type:
        struct = extract_structural_elements(ifc_bytes)
        if struct:
            parts.append("**Éléments structurels :**")
            for elem in struct[:30]:
                qto = elem.get("quantities", {})
                parts.append(f"- {elem['type']} '{elem['name']}' — {qto}")
            parts.append("")

    return "\n".join(parts)
