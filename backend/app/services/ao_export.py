"""Export du dossier d'appel d'offres complet en archive ZIP.

Assemble en une seule action tous les documents produits pour un projet
(CCTP, DPGF, justificatif thermique, note de calcul, checklist AEAI, etc.)
dans une archive ZIP organisée par phase SIA, avec un sommaire.

Au lieu de télécharger document par document, l'ingénieur obtient le dossier
complet prêt à transmettre.
"""
from __future__ import annotations

import io
import logging
import zipfile
from datetime import datetime
from typing import Any

import httpx

from app.database import get_supabase_admin

logger = logging.getLogger(__name__)


# Préfixe de dossier dans le ZIP par phase SIA (pour organiser l'archive)
PHASE_FOLDER = {
    "avant_projet": "01_Avant-projet_SIA31",
    "projet_ouvrage": "02_Projet_SIA32",
    "autorisation": "03_Autorisation_SIA33",
    "appel_offres": "04_Appel-offres_SIA41",
    "execution": "05_Execution_SIA51",
    "cloture": "06_Cloture_SIA53",
}

# À quelle phase rattacher chaque type de tâche
TASK_PHASE = {
    "controle_reglementaire_vaud": "avant_projet",
    "controle_reglementaire_geneve": "avant_projet",
    "simulation_energetique_rapide": "avant_projet",
    "justificatif_sia_380_1": "projet_ouvrage",
    "calcul_cecb": "projet_ouvrage",
    "note_calcul_sia_260_267": "projet_ouvrage",
    "dossier_mise_enquete": "autorisation",
    "aeai_checklist_generation": "autorisation",
    "aeai_rapport": "autorisation",
    "idc_geneve_rapport": "autorisation",
    "redaction_cctp": "appel_offres",
    "chiffrage_dpgf": "appel_offres",
    "coordination_inter_lots": "appel_offres",
    "reponse_observations_autorite": "execution",
    "metres_automatiques_ifc": "execution",
    "doe_compilation": "cloture",
}

TASK_LABELS = {
    "controle_reglementaire_vaud": "Controle_urbanistique",
    "simulation_energetique_rapide": "Simulation_energetique",
    "justificatif_sia_380_1": "Justificatif_thermique_SIA380-1",
    "calcul_cecb": "CECB",
    "note_calcul_sia_260_267": "Note_calcul_structure",
    "dossier_mise_enquete": "Dossier_mise_enquete",
    "aeai_checklist_generation": "Checklist_AEAI",
    "aeai_rapport": "Rapport_AEAI",
    "idc_geneve_rapport": "IDC",
    "redaction_cctp": "CCTP",
    "chiffrage_dpgf": "DPGF",
    "coordination_inter_lots": "Coordination_inter-lots",
    "doe_compilation": "DOE",
}


async def build_ao_dossier_zip(
    project_id: str,
    organization_id: str,
    *,
    only_approved: bool = True,
) -> tuple[bytes, str, dict[str, Any]]:
    """Construit le ZIP du dossier complet d'un projet.

    Args:
        only_approved: si True, n'inclut que les documents validés par l'ingénieur.

    Returns (zip_bytes, filename, summary).
    """
    admin = get_supabase_admin()

    project = (
        admin.table("projects").select("*")
        .eq("id", project_id).eq("organization_id", organization_id)
        .maybe_single().execute()
    )
    if not project.data:
        raise ValueError("Projet introuvable")
    proj = project.data

    # Récupère les tâches complétées avec un document
    query = (
        admin.table("tasks")
        .select("id, task_type, result_url, completed_at, review_status, confidence_score")
        .eq("project_id", project_id)
        .eq("organization_id", organization_id)
        .eq("status", "completed")
        .not_.is_("result_url", "null")
    )
    tasks = query.execute()
    rows = tasks.data or []

    if only_approved:
        rows = [r for r in rows if r.get("review_status") == "approved"]

    included = []
    skipped = []

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        async with httpx.AsyncClient(timeout=30) as client:
            for task in rows:
                url = task.get("result_url")
                if not url:
                    continue
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    content = resp.content
                except Exception as exc:
                    logger.warning("Téléchargement échoué task=%s : %s", task["id"], exc)
                    skipped.append(task["task_type"])
                    continue

                phase = TASK_PHASE.get(task["task_type"], "00_Divers")
                folder = PHASE_FOLDER.get(phase, "00_Divers")
                label = TASK_LABELS.get(task["task_type"], task["task_type"])
                # Détection extension simple
                ext = "pdf" if content[:4] == b"%PDF" else (
                    "xlsx" if content[:2] == b"PK" else "bin"
                )
                fname = f"{folder}/{label}.{ext}"
                zf.writestr(fname, content)
                included.append({"task_type": task["task_type"], "file": fname,
                                 "confidence": task.get("confidence_score")})

        # Sommaire (README)
        summary_txt = _build_summary(proj, included, skipped, only_approved)
        zf.writestr("00_SOMMAIRE.txt", summary_txt)

    buf.seek(0)
    safe_name = (proj.get("name") or "projet").replace(" ", "_").replace("/", "-")
    filename = f"Dossier_{safe_name}_{datetime.now().strftime('%Y%m%d')}.zip"

    summary = {
        "project_name": proj.get("name"),
        "documents_included": len(included),
        "documents_skipped": len(skipped),
        "only_approved": only_approved,
        "included": included,
    }
    return buf.getvalue(), filename, summary


def _build_summary(proj: dict, included: list, skipped: list, only_approved: bool) -> str:
    lines = [
        f"DOSSIER D'APPEL D'OFFRES — {proj.get('name', '')}",
        "=" * 60,
        f"Adresse : {proj.get('address', '—')}",
        f"Commune : {proj.get('commune', '—')} ({proj.get('canton', '—')})",
        f"SRE : {proj.get('sre_m2', '—')} m²",
        f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Filtre : {'documents validés uniquement' if only_approved else 'tous les documents'}",
        "",
        f"DOCUMENTS INCLUS ({len(included)})",
        "-" * 60,
    ]
    for doc in included:
        conf = f" [confiance {doc['confidence']}%]" if doc.get("confidence") else ""
        lines.append(f"  • {doc['file']}{conf}")
    if skipped:
        lines += ["", f"NON INCLUS ({len(skipped)}) :", "-" * 60]
        for s in skipped:
            lines.append(f"  • {s} (téléchargement indisponible)")
    lines += [
        "",
        "=" * 60,
        "Document généré par LESO. Les documents engageant la",
        "responsabilité de l'ingénieur ont été validés avant inclusion.",
    ]
    return "\n".join(lines)
