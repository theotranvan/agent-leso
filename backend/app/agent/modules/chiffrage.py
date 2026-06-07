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


DPGF_SYSTEM_PROMPT = """Tu es un métreur-chiffreur d'un BET de Suisse romande. On te fournit une \
BASE DE PRIX UNITAIRES RÉELS (CHF, indice 2025, ajustés au canton) pour les articles du lot.

Ton travail :
1. Identifier les articles pertinents pour ce projet parmi ceux fournis.
2. Estimer les QUANTITÉS de chaque article à partir du métré / programme / surface fournis.
3. NE PAS inventer de prix : utilise les prix médians fournis. Si tu dois estimer une quantité \
   sans donnée précise, indique-le dans une note et reste conservateur.

Retourne UNIQUEMENT un JSON strict (pas de markdown) :
{
  "lines": [
    {"is_section": true, "designation": "CFC 231 — Production de chaleur"},
    {"article": "231.110", "designation": "PAC air-eau ...", "unite": "kW", "quantite": 50,
     "prix_unitaire": 1700, "hypothese": "Puissance estimée selon SRE et standard"},
    ...
  ],
  "hypotheses_globales": ["..."],
  "taux_incertitude_pct": 15
}

Le champ prix_unitaire DOIT correspondre au prix médian fourni pour l'article (ne l'invente pas)."""

async def _generate_dpgf(task, params, project_name, org_name, metre_text, rag_context) -> dict[str, Any]:
    lot = params.get("lot", "")
    niveau = params.get("niveau_prestation", "standard")
    org_id = task["organization_id"]

    # Charge le canton du projet
    project_id = task.get("project_id")
    canton = params.get("canton", "VD")
    if project_id:
        proj = get_supabase_admin().table("projects").select("canton").eq("id", project_id).maybe_single().execute()
        if proj.data and proj.data.get("canton"):
            canton = proj.data["canton"]

    # Injecte la base de prix réelle pour le lot
    from app.knowledge_base.dpgf import list_prix_for_lot
    prix_catalogue = list_prix_for_lot(lot, niveau, canton)

    if prix_catalogue:
        prix_block = f"BASE DE PRIX RÉELLE — Lot {lot}, niveau {niveau}, canton {canton} (CHF HT) :\n"
        for p in prix_catalogue:
            prix_block += (
                f"- [{p['code']}] {p['designation']} | unité: {p['unite']} | "
                f"prix médian: {p['prix_median']} CHF (fourchette {p['prix_min']}-{p['prix_max']})"
            )
            if p.get("notes"):
                prix_block += f" | note: {p['notes']}"
            prix_block += "\n"
    else:
        prix_block = (
            f"Aucune base de prix disponible pour le lot '{lot}'. "
            f"Indique clairement que les prix doivent être complétés manuellement."
        )

    user_content = f"""Générer le DPGF chiffré pour ce projet.

**Projet :** {project_name}
**Lot :** {lot}
**Niveau de prestation :** {niveau}
**Canton :** {canton}

**Métré / descriptif fourni :**
{metre_text[:12000] if metre_text else "Aucun métré fourni — estime les quantités depuis le programme et la surface, et liste tes hypothèses."}

**{prix_block}**

{rag_context}

Retourne le JSON strict avec les quantités estimées et les prix médians fournis."""

    # Régénération
    from app.agent.prompts import build_regeneration_instructions
    regen_block = build_regeneration_instructions(params.get("regeneration_context"))
    if regen_block:
        user_content += regen_block

    llm_result = await call_llm(
        task_type="chiffrage_dpgf",
        system_prompt=DPGF_SYSTEM_PROMPT,
        user_content=user_content,
        max_tokens=8000,
        temperature=0.1,
        organization_id=org_id,
        task_id=task.get("id"),
    )

    data = _parse_json_lenient(llm_result["text"])
    lines = data.get("lines", [])

    # Validation : on force les prix unitaires à correspondre à la base réelle
    prix_lookup = {p["code"]: p for p in prix_catalogue}
    for line in lines:
        code = line.get("article")
        if code and code in prix_lookup:
            # On écrase le prix LLM par le prix réel de la base (sécurité)
            line["prix_unitaire"] = prix_lookup[code]["prix_median"]
            line["prix_min"] = prix_lookup[code]["prix_min"]
            line["prix_max"] = prix_lookup[code]["prix_max"]

    excel_bytes = generate_dpgf_excel(
        project_name=project_name,
        lot=lot,
        lines=lines,
        organization_name=org_name,
    )

    # PDF récapitulatif
    total_ht = sum((ln.get("quantite") or 0) * (ln.get("prix_unitaire") or 0) for ln in lines if not ln.get("is_section"))
    total_min = sum((ln.get("quantite") or 0) * (ln.get("prix_min") or ln.get("prix_unitaire") or 0) for ln in lines if not ln.get("is_section"))
    total_max = sum((ln.get("quantite") or 0) * (ln.get("prix_max") or ln.get("prix_unitaire") or 0) for ln in lines if not ln.get("is_section"))
    incertitude = data.get("taux_incertitude_pct", 15)
    hypotheses = data.get("hypotheses_globales", [])

    # Garde-fou : si le lot n'est pas couvert par la base de prix (ou si aucun
    # article n'a pu être chiffré), on signale clairement « prix à compléter »
    # plutôt que de laisser un tableau silencieusement à zéro.
    if not prix_catalogue or total_ht <= 0:
        avertissement = (
            f"> ⚠ **Prix à compléter manuellement.** Le lot « {lot} » n'est pas couvert "
            "par la base de prix de référence (lots chiffrés automatiquement : gros œuvre, "
            "façade/enveloppe, second œuvre, chauffage/CVS, ventilation, sanitaire, électricité, "
            "MCR/GTB, ascenseurs). Les quantités sont estimées, mais les prix unitaires doivent "
            "être saisis par le métreur."
        )
    else:
        avertissement = (
            "> Prix unitaires issus de la base de référence Suisse romande (indice 2025), "
            "ajustés au canton. À valider en consultation."
        )

    recap_md = f"""# Récapitulatif DPGF — Lot {lot}

**Projet :** {project_name}
**Nombre d'articles :** {len([ln for ln in lines if not ln.get('is_section')])}
**Montant total HT estimé (médian) :** {total_ht:,.0f} CHF
**Fourchette :** {total_min:,.0f} – {total_max:,.0f} CHF
**Taux d'incertitude estimé :** ±{incertitude} %

{avertissement}

## Hypothèses retenues
""" + ("\n".join(f"- {h}" for h in hypotheses) if hypotheses else "- Aucune hypothèse spécifique signalée.") + """

## Détail par article

| N° | Désignation | Unité | Quantité | PU médian | Total |
|----|-------------|-------|----------|-----------|-------|
""" + "\n".join(
        f"| {ln.get('article', '')} | {ln.get('designation', '')[:70]} | {ln.get('unite', '')} | {ln.get('quantite', '')} | {ln.get('prix_unitaire', '')} CHF | {((ln.get('quantite') or 0) * (ln.get('prix_unitaire') or 0)):,.0f} CHF |"
        for ln in lines[:80] if not ln.get("is_section")
    )

    # Charte client pour le PDF
    from app.knowledge_base.templates.charter import get_org_branding
    branding = await get_org_branding(org_id)
    branding_dict = {
        "primary_color": branding.primary_color,
        "accent_color": branding.accent_color,
        "logo_url": branding.logo_url,
        "footer_text": branding.footer_text or branding.organization_name,
        "full_name": branding.organization_full_name,
    }

    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(recap_md),
        title=f"DPGF — Lot {lot}",
        subtitle=f"Montant total HT médian : {total_ht:,.0f} CHF",
        project_name=project_name,
        lot=lot,
        reference=f"DPGF-{datetime.now().strftime('%Y%m%d-%H%M')}",
        branding=branding_dict,
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
        "preview": f"DPGF généré — {len([ln for ln in lines if not ln.get('is_section')])} articles — Total HT médian : {total_ht:,.0f} CHF (fourchette {total_min:,.0f}–{total_max:,.0f})\n\nFichiers : Excel (actif) + PDF récap",
        "model": llm_result["model"],
        "tokens_used": llm_result["tokens_used"],
        "cost_eur": llm_result["cost_eur"],
        "email_bytes": excel_bytes,
        "email_filename": excel_filename,
        "result_html": markdown_to_html(recap_md),
    }


async def _generate_dqe(task, params, project_name, org_name, metre_text, rag_context) -> dict[str, Any]:
    lots_input = params.get("lots", [])
    if not lots_input:
        # Respecte le lot choisi par l'ingénieur s'il n'a pas fourni de liste,
        # sinon liste type multi-lots.
        single = params.get("lot")
        lots_input = [single] if single else [
            "gros_oeuvre", "second_oeuvre", "cvc", "electricite", "plomberie",
        ]

    # Canton du projet (pour ajuster la base de prix réelle)
    org_id = task["organization_id"]
    project_id = task.get("project_id")
    canton = params.get("canton", "VD")
    if project_id:
        proj = get_supabase_admin().table("projects").select("canton").eq("id", project_id).maybe_single().execute()
        if proj.data and proj.data.get("canton"):
            canton = proj.data["canton"]

    # Base de prix réelle par lot (même source que le DPGF) : on l'injecte dans
    # le prompt ET on s'en sert pour FORCER les prix après génération, comme pour
    # le DPGF. Les lots non couverts restent estimés par le LLM (signalés).
    from app.knowledge_base.dpgf import list_prix_for_lot
    prix_par_lot: dict[str, dict] = {}
    lots_sans_base: list[str] = []
    prix_blocks = []
    for lot in lots_input:
        cat = list_prix_for_lot(lot, params.get("niveau_prestation", "standard"), canton)
        if cat:
            prix_par_lot[lot] = {p["code"]: p for p in cat}
            bloc = f"Lot « {lot} » — base de prix réelle (CHF HT, canton {canton}) :\n"
            for p in cat:
                bloc += f"  - [{p['code']}] {p['designation']} | {p['unite']} | médian {p['prix_median']} CHF\n"
            prix_blocks.append(bloc)
        else:
            lots_sans_base.append(lot)

    prix_section = (
        "\n".join(prix_blocks) if prix_blocks
        else "Aucune base de prix disponible pour ces lots — estime et signale-le."
    )
    if lots_sans_base:
        prix_section += (
            f"\n\nLots SANS base de prix (à estimer prudemment, prix à valider) : "
            f"{', '.join(lots_sans_base)}."
        )

    system_prompt = get_system_prompt("chiffrage_dqe")
    user_content = f"""Générer le DQE multi-lots pour ce projet.

**Projet :** {project_name}
**Lots à chiffrer :** {', '.join(lots_input)}
**Canton :** {canton}

**Métré / descriptif fourni :**
{metre_text[:15000] if metre_text else "Aucun métré fourni — poser les hypothèses."}

**BASE DE PRIX RÉELLE (utilise ces codes et prix médians, n'invente pas) :**
{prix_section}

{rag_context}

Retourner un JSON. Pour les lots avec base de prix, REPRENDS les codes d'article fournis :
{{
  "lots": {{
    "nom_lot_1": [ {{"article": "231.110", "designation": "...", "unite": "...", "quantite": X, "prix_unitaire": Y}}, ... ],
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

    # Force les prix unitaires sur la base réelle (sécurité anti-invention),
    # comme pour le DPGF. On tolère que la clé de lot du LLM diffère légèrement.
    for lot_name, lines in lots_data.items():
        lookup = prix_par_lot.get(lot_name) or prix_par_lot.get(lot_name.lower().replace(" ", "_"))
        if not lookup:
            continue
        for ln in lines:
            code = ln.get("article")
            if code and code in lookup:
                ln["prix_unitaire"] = lookup[code]["prix_median"]

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
        sum((ln.get("quantite") or 0) * (ln.get("prix_unitaire") or 0) for ln in lines)
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
        "preview": f"DQE généré — {len(lots_data)} lots — Total HT : {total:,.0f} CHF",
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
