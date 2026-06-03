"""Export des échéances projet au format iCalendar (.ics).

Le format .ics est universel : l'ingénieur importe le fichier dans Google
Calendar, Outlook ou Apple Calendar, ou s'abonne au flux pour une synchro
automatique. Pas besoin d'OAuth complexe par fournisseur pour démarrer.

Génère des événements pour : échéances réglementaires (AEAI, permis),
dates de dépôt, réceptions de chantier.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from app.database import get_supabase_admin

logger = logging.getLogger(__name__)


def _escape_ics(text: str) -> str:
    """Échappe les caractères spéciaux iCalendar."""
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _format_date(d: date) -> str:
    return d.strftime("%Y%m%d")


def build_ics_for_organization(organization_id: str) -> str:
    """Construit un flux .ics avec toutes les échéances non terminées d'une org."""
    admin = get_supabase_admin()

    deadlines = (
        admin.table("project_deadlines")
        .select("id, label, due_date, project_id, phase_key")
        .eq("organization_id", organization_id)
        .eq("completed", False)
        .execute()
    )
    rows = deadlines.data or []

    # Récupère les noms de projets
    project_names: dict[str, str] = {}
    if rows:
        pids = list({r["project_id"] for r in rows if r.get("project_id")})
        if pids:
            projects = (
                admin.table("projects").select("id, name")
                .in_("id", pids).execute()
            )
            project_names = {p["id"]: p["name"] for p in (projects.data or [])}

    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LESO//Echeances//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:LESO — Échéances",
    ]

    for r in rows:
        try:
            due = date.fromisoformat(r["due_date"])
        except (ValueError, TypeError):
            continue
        proj_name = project_names.get(r.get("project_id"), "")
        summary = f"{r['label']}" + (f" — {proj_name}" if proj_name else "")

        lines += [
            "BEGIN:VEVENT",
            f"UID:betagent-deadline-{r['id']}@bet-agent.ch",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{_format_date(due)}",
            f"SUMMARY:{_escape_ics(summary)}",
            f"DESCRIPTION:{_escape_ics(f'Échéance suivie par LESO pour le projet {proj_name}.')}",
            # Rappel 7 jours avant
            "BEGIN:VALARM",
            "TRIGGER:-P7D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_escape_ics(f'Dans 7 jours : {summary}')}",
            "END:VALARM",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def build_ics_for_project(project_id: str, organization_id: str) -> str:
    """Variante : flux .ics pour un seul projet."""
    admin = get_supabase_admin()
    deadlines = (
        admin.table("project_deadlines")
        .select("id, label, due_date, phase_key")
        .eq("organization_id", organization_id)
        .eq("project_id", project_id)
        .eq("completed", False)
        .execute()
    )
    project = (
        admin.table("projects").select("name")
        .eq("id", project_id).maybe_single().execute()
    )
    proj_name = (project.data or {}).get("name", "")
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//LESO//Echeances//FR", "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape_ics(proj_name)} — Échéances",
    ]
    for r in deadlines.data or []:
        try:
            due = date.fromisoformat(r["due_date"])
        except (ValueError, TypeError):
            continue
        lines += [
            "BEGIN:VEVENT",
            f"UID:betagent-deadline-{r['id']}@bet-agent.ch",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{_format_date(due)}",
            f"SUMMARY:{_escape_ics(r['label'] + ' — ' + proj_name)}",
            "BEGIN:VALARM", "TRIGGER:-P7D", "ACTION:DISPLAY",
            f"DESCRIPTION:{_escape_ics('Échéance dans 7 jours')}",
            "END:VALARM", "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def add_deadline(
    *, organization_id: str, project_id: str, label: str,
    due_date: str, phase_key: str | None = None,
) -> dict[str, Any]:
    """Ajoute une échéance à un projet."""
    admin = get_supabase_admin()
    row = {
        "organization_id": organization_id,
        "project_id": project_id,
        "label": label,
        "due_date": due_date,
        "phase_key": phase_key,
    }
    result = admin.table("project_deadlines").insert(row).execute()
    return (result.data or [{}])[0]
