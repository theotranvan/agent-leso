"""Agent dossier mise en enquête (APA Genève, APC Vaud, autres cantons romands).

Ce module est le livrable le plus chronophage de la phase DD/AP : 5-10 jours/affaire.
L'agent produit :
  - Mémoire justificatif structuré par chapitres réglementaires
  - Tableaux SIA 451 (surfaces, volumes, affectations) agrégés
  - Liste des pièces à fournir pour le dépôt
  - Checklist pré-dépôt consolidée

Le dossier est préparatoire : l'architecte + l'ingénieur signent avant dépôt officiel.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from app.agent.router import call_llm
from app.agent.swiss.prompts_ch import get_prompt_ch
from app.ch.cantons.autres_romands import checklist_for_canton
from app.database import get_storage, get_supabase_admin
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)


# Pièces à fournir par canton (version canonique, à confirmer avec la pratique locale)
PIECES_DEPOT_APA_GE: list[dict[str, Any]] = [
    {"code": "A01", "nom": "Formulaire APA signé", "format": "PDF", "responsable": "architecte"},
    {"code": "A02", "nom": "Extrait du Registre foncier récent (<3 mois)", "format": "PDF", "responsable": "requérant"},
    {"code": "A03", "nom": "Extrait cadastral officiel", "format": "PDF", "responsable": "requérant"},
    {"code": "A04", "nom": "Plans de situation 1:500 et 1:2500", "format": "PDF", "responsable": "architecte"},
    {"code": "A05", "nom": "Plans des étages, coupes, façades 1:100", "format": "PDF", "responsable": "architecte"},
    {"code": "A06", "nom": "Plan des aménagements extérieurs 1:200", "format": "PDF", "responsable": "architecte"},
    {"code": "A07", "nom": "Tableau des surfaces SIA 416", "format": "PDF/XLSX", "responsable": "architecte"},
    {"code": "A08", "nom": "Calcul indices (IUS, IBUS, ILE selon règlement de zone)", "format": "PDF", "responsable": "architecte"},
    {"code": "A09", "nom": "Formulaire énergie (I-700) + justificatif SIA 380/1", "format": "PDF", "responsable": "thermicien"},
    {"code": "A10", "nom": "Concept ventilation / refroidissement (si applicable)", "format": "PDF", "responsable": "CVS"},
    {"code": "A11", "nom": "Rapport incendie AEAI", "format": "PDF", "responsable": "expert_incendie"},
    {"code": "A12", "nom": "Concept mobilité / stationnement", "format": "PDF", "responsable": "architecte"},
    {"code": "A13", "nom": "Évaluation LDTR (si transformation logement)", "format": "PDF", "responsable": "architecte"},
    {"code": "A14", "nom": "Étude géotechnique (si fouilles/nappe)", "format": "PDF", "responsable": "géotechnicien"},
    {"code": "A15", "nom": "Dossier paysage / arbres (si abattage)", "format": "PDF", "responsable": "architecte"},
    {"code": "A16", "nom": "Photos existant et insertion", "format": "PDF", "responsable": "architecte"},
    {"code": "A17", "nom": "Mémoire justificatif technique (ce document)", "format": "PDF", "responsable": "bet_principal"},
]

PIECES_DEPOT_APC_VD: list[dict[str, Any]] = [
    {"code": "V01", "nom": "Formulaire de demande d'autorisation de construire", "format": "PDF", "responsable": "architecte"},
    {"code": "V02", "nom": "Plans à l'échelle réglementaire (1:100 et 1:200)", "format": "PDF", "responsable": "architecte"},
    {"code": "V03", "nom": "Tableau des surfaces selon LATC / RLATC", "format": "PDF", "responsable": "architecte"},
    {"code": "V04", "nom": "Formulaire LVLEne + calcul SIA 380/1", "format": "PDF", "responsable": "thermicien"},
    {"code": "V05", "nom": "Concept ECA / AEAI", "format": "PDF", "responsable": "expert_incendie"},
    {"code": "V06", "nom": "Preuve PPE si construction privée", "format": "PDF", "responsable": "requérant"},
    {"code": "V07", "nom": "Concept énergétique et renouvelable", "format": "PDF", "responsable": "thermicien"},
    {"code": "V08", "nom": "Mémoire justificatif technique", "format": "PDF", "responsable": "bet_principal"},
]


def _pieces_for_canton(canton: str) -> list[dict[str, Any]]:
    mapping = {
        "GE": PIECES_DEPOT_APA_GE,
        "VD": PIECES_DEPOT_APC_VD,
    }
    return mapping.get(canton.upper(), PIECES_DEPOT_APA_GE)


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Pipeline complet dossier mise en enquête.

    Input params :
      - project_data: dict (canton, address, affectation, operation_type, sre_m2,
                            nb_logements, volume_sia, terrain_m2, zone, indices)
      - existing_documents: list[dict] (documents déjà uploadés dans le projet)
      - specificities: str (contraintes particulières du projet)
      - author: str (ingénieur signataire)
    """
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")

    project_data = params.get("project_data") or {}
    if not project_data:
        raise ValueError("project_data requis (canton, affectation, sre_m2...)")

    canton = str(project_data.get("canton", "GE")).upper()
    project_name = params.get("project_name") or project_data.get("project_name", "Projet")
    author = params.get("author", "")

    # 1. Liste des pièces attendues
    pieces_attendues = _pieces_for_canton(canton)

    # 2. Checklist réglementaire cantonale
    checklist = checklist_for_canton(canton, project_data)

    # 3. Analyse des documents existants (matching avec les pièces attendues)
    existing_docs = params.get("existing_documents") or []
    doc_coverage = _match_docs_to_pieces(existing_docs, pieces_attendues)

    # 4. Génération du mémoire justificatif via LLM Sonnet
    system = get_prompt_ch("dossier_enquete")
    user_content = f"""Produire un MÉMOIRE JUSTIFICATIF TECHNIQUE pour dossier de mise en enquête publique.

CANTON : {canton}
PROCÉDURE : {'APA (Genève)' if canton == 'GE' else 'APC (Vaud)' if canton == 'VD' else 'Mise en enquête'}

PROJET
- Nom : {project_name}
- Adresse : {project_data.get('address', '')}
- Affectation : {project_data.get('affectation', '?')}
- Opération : {project_data.get('operation_type', '?')}
- SRE : {project_data.get('sre_m2', '?')} m²
- Volume SIA 416 : {project_data.get('volume_sia', '?')} m³
- Terrain : {project_data.get('terrain_m2', '?')} m²
- Zone affectation : {project_data.get('zone', '?')}
- Nombre de logements : {project_data.get('nb_logements', 'n/a')}
- Indices projet : IUS={project_data.get('indices', {}).get('ius', 'n/a')}, IBUS={project_data.get('indices', {}).get('ibus', 'n/a')}

SPÉCIFICITÉS DU PROJET
{params.get('specificities', 'Aucune spécificité signalée.')}

CHECKLIST RÉGLEMENTAIRE (produite par le moteur interne)
{json.dumps(checklist, ensure_ascii=False, indent=2)}

PIÈCES À FOURNIR ({len(pieces_attendues)} pièces)
{json.dumps(pieces_attendues, ensure_ascii=False, indent=2)}

COUVERTURE DOCUMENTAIRE ACTUELLE
- Pièces présentes : {doc_coverage['present']} / {len(pieces_attendues)}
- Pièces manquantes : {', '.join(doc_coverage['missing_codes']) if doc_coverage['missing_codes'] else 'aucune'}

Structure du mémoire :
1. Description générale du projet (contexte, intentions, parti architectural synthétique)
2. Cadre réglementaire applicable (loi, règlement de zone, normes SIA)
3. Implantation et accessibilité (gabarits, distances, mobilité)
4. Programme des surfaces (SIA 416, indices, nombre de logements)
5. Aspects énergétiques (SIA 380/1, standard visé, rénovation si applicable)
6. Sécurité incendie (référence AEAI, catégorie de danger, distances)
7. Assainissement et environnement (eaux, bruit, arbres)
8. Stationnement et mobilité douce
9. Pièces jointes au dossier (référence aux codes A01/A02... ou V01/V02...)
10. Déclarations et signatures

Consignes :
- Ton factuel et technique, pas commercial
- Référencer les normes SIA/AEAI et les lois cantonales sans reproduction de texte
- Lister clairement les pièces manquantes en conclusion (rubrique "Points d'attention")
- Prévoir visa ingénieur + architecte en bas"""

    llm = await call_llm(
        task_type="dossier_mise_enquete",
        system_prompt=system,
        user_content=user_content,
        max_tokens=6000,
        temperature=0.15,
    )

    md = llm["text"]

    # 5. Génération tableau SIA 451 des surfaces (PDF séparé)
    sia_451_table_md = _build_sia_451_table(project_data)

    # 6. Liste consolidée des pièces (checklist de dépôt)
    depot_checklist_md = _build_depot_checklist(pieces_attendues, doc_coverage)

    # 7. Assemblage final
    full_md = f"""# Dossier de mise en enquête publique

**Projet** : {project_name}
**Adresse** : {project_data.get('address', '')}
**Canton** : {canton}
**Procédure** : {'APA (Autorisation Préalable de construire) - Genève' if canton == 'GE' else 'APC (Autorisation Préalable de Construire) - Vaud' if canton == 'VD' else 'Mise en enquête'}
**Date** : {datetime.now().strftime('%d.%m.%Y')}
**Auteur** : {author or "Bureau d'études techniques"}

---

## I. Mémoire justificatif technique

{md}

---

## II. Tableau des surfaces SIA 416

{sia_451_table_md}

---

## III. Checklist de dépôt

{depot_checklist_md}

---

*Ce dossier préparatoire a été généré par BET Agent. L'architecte et les ingénieurs signataires
engagent seuls leur responsabilité professionnelle sur la conformité du dossier au moment du dépôt officiel.*
"""

    # 8. PDF final
    pdf_bytes = render_pdf_from_html(
        body_html=markdown_to_html(full_md),
        title="Dossier de mise en enquête publique",
        subtitle=f"Canton {canton} — {project_data.get('affectation', '')}",
        project_name=project_name,
        project_address=project_data.get("address", ""),
        author=author,
        reference=f"DME-{canton}-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    storage = get_storage()
    admin = get_supabase_admin()

    filename = f"dossier_enquete_{canton}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/dossier_enquete/{task['id']}/{filename}"
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
        "preview": md[:500],
        "model": llm["model"],
        "tokens_used": llm["tokens_used"],
        "cost_eur": llm["cost_eur"],
        "email_bytes": pdf_bytes,
        "email_filename": filename,
        "nb_pieces_attendues": len(pieces_attendues),
        "nb_pieces_manquantes": len(doc_coverage["missing_codes"]),
        "coverage_pct": round(doc_coverage["present"] / len(pieces_attendues) * 100, 1),
    }


def _match_docs_to_pieces(
    docs: list[dict[str, Any]],
    pieces: list[dict[str, Any]],
) -> dict[str, Any]:
    """Match heuristique des documents uploadés sur les pièces attendues.

    Utilise mots-clés dans le nom du fichier.
    """
    keywords = {
        "A01": ["apa", "formulaire"],
        "A04": ["situation", "1500", "1:500", "plan_situation"],
        "A05": ["plan", "coupe", "facade", "étage", "etage"],
        "A07": ["surface", "sia_416", "sia416"],
        "A08": ["indice", "ius", "ibus"],
        "A09": ["energie", "380", "sia380", "i-700", "i700"],
        "A10": ["ventilation", "refroidissement", "cvs"],
        "A11": ["aeai", "incendie"],
        "A12": ["mobilite", "stationnement", "parking"],
        "A13": ["ldtr"],
        "A14": ["geotechnique"],
        "A15": ["paysage", "arbre"],
        "A16": ["photo"],
        "V01": ["apc", "formulaire"],
        "V02": ["plan"],
        "V04": ["lvlene", "380"],
        "V05": ["eca", "aeai"],
        "V07": ["energie", "renouvelable"],
    }

    present_codes: set[str] = set()
    for doc in docs:
        name = (doc.get("filename") or "").lower()
        for code, kws in keywords.items():
            if any(kw in name for kw in kws):
                present_codes.add(code)

    all_codes = {p["code"] for p in pieces}
    return {
        "present": len(present_codes & all_codes),
        "present_codes": sorted(present_codes & all_codes),
        "missing_codes": sorted(all_codes - present_codes),
    }


def _build_sia_451_table(project_data: dict[str, Any]) -> str:
    """Produit un tableau markdown SIA 416 (surfaces de référence)."""
    sre = project_data.get("sre_m2") or 0
    volume = project_data.get("volume_sia") or 0
    terrain = project_data.get("terrain_m2") or 0
    surfaces = project_data.get("surfaces") or {}

    su = surfaces.get("su_m2") or round(sre * 0.8, 1)
    sb = surfaces.get("sb_m2") or round(sre * 1.05, 1)
    sp = surfaces.get("sp_m2") or round(sre * 1.1, 1)

    lines = [
        "| Code | Grandeur | Unité | Valeur |",
        "|------|----------|-------|--------|",
        f"| SP | Surface de plancher (SIA 416) | m² | {sp} |",
        f"| SB | Surface brute de plancher | m² | {sb} |",
        f"| SRE | Surface de référence énergétique (SIA 380/1) | m² | {sre} |",
        f"| SU | Surface utile | m² | {su} |",
        f"| V_SIA | Volume bâti selon SIA 416 | m³ | {volume} |",
        f"| ST | Surface totale du terrain | m² | {terrain} |",
    ]

    indices = project_data.get("indices") or {}
    if indices:
        lines.append("\n### Indices d'utilisation\n")
        lines.append("| Indice | Valeur projet | Limite zone |")
        lines.append("|--------|---------------|-------------|")
        for k, v in indices.items():
            limit = project_data.get("indices_limites", {}).get(k, "—")
            lines.append(f"| {k.upper()} | {v} | {limit} |")

    return "\n".join(lines)


def _build_depot_checklist(
    pieces: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> str:
    """Produit la checklist markdown des pièces à fournir."""
    present = set(coverage.get("present_codes") or [])
    lines = ["| Code | Pièce | Responsable | Statut |", "|------|-------|-------------|--------|"]
    for p in pieces:
        status = "✓ Disponible" if p["code"] in present else "✗ À fournir"
        lines.append(f"| {p['code']} | {p['nom']} | {p['responsable']} | {status} |")
    return "\n".join(lines)
