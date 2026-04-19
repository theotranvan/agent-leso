"""Envoi d'emails via Resend."""
import base64
import logging
from typing import Optional

import resend

from app.config import settings

logger = logging.getLogger(__name__)

resend.api_key = settings.RESEND_API_KEY


def send_email(
    to: list[str] | str,
    subject: str,
    html: str,
    attachments: Optional[list[dict]] = None,
    reply_to: Optional[str] = None,
) -> Optional[str]:
    """Envoie un email. attachments = [{'filename': ..., 'content': bytes}].
    Retourne l'ID du message Resend ou None en cas d'échec.
    """
    recipients = to if isinstance(to, list) else [to]
    params: dict = {
        "from": settings.FROM_EMAIL,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        params["reply_to"] = reply_to

    if attachments:
        params["attachments"] = [
            {
                "filename": att["filename"],
                "content": base64.b64encode(att["content"]).decode("ascii") if isinstance(att["content"], bytes) else att["content"],
            }
            for att in attachments
        ]

    try:
        response = resend.Emails.send(params)
        email_id = response.get("id") if isinstance(response, dict) else None
        logger.info(f"Email envoyé à {recipients}: {email_id}")
        return email_id
    except Exception as e:
        logger.error(f"Erreur envoi email: {e}")
        return None


def send_task_completed_email(
    to: list[str],
    task_type: str,
    project_name: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
    preview_text: Optional[str] = None,
) -> Optional[str]:
    """Email standardisé de livraison de tâche."""
    task_labels = {
        "redaction_cctp": "CCTP",
        "note_calcul_structure": "Note de calcul structure",
        "calcul_thermique_re2020": "Calcul thermique RE2020",
        "calcul_acoustique": "Note acoustique",
        "chiffrage_dpgf": "DPGF",
        "chiffrage_dqe": "DQE",
        "coordination_inter_lots": "Rapport de coordination",
        "compte_rendu_reunion": "Compte-rendu de réunion",
        "doe_compilation": "DOE",
        "memoire_technique": "Mémoire technique",
        "verification_eurocode": "Vérification Eurocode",
    }
    label = task_labels.get(task_type, task_type.replace("_", " ").title())

    preview_html = f"<p>{preview_text}</p>" if preview_text else ""
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #0a0a0a;">
      <h2 style="margin: 0 0 16px; font-size: 20px; font-weight: 600;">Document prêt : {label}</h2>
      <p style="margin: 0 0 16px; color: #525252;">Projet : <strong>{project_name}</strong></p>
      {preview_html}
      <p style="margin: 24px 0 0; color: #525252; font-size: 13px;">Document généré automatiquement par BET Agent. Vous le retrouvez également dans votre espace projet.</p>
    </div>
    """

    attachments = None
    if attachment_bytes and attachment_filename:
        attachments = [{"filename": attachment_filename, "content": attachment_bytes}]

    return send_email(to, f"[BET Agent] {label} - {project_name}", html, attachments=attachments)


def send_alert_email(to: list[str], subject: str, body_html: str) -> Optional[str]:
    """Email d'alerte (réglementaire, incident)."""
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
      <h2 style="margin: 0 0 16px; font-size: 20px; font-weight: 600; color: #b45309;">⚠ Alerte</h2>
      {body_html}
    </div>
    """
    return send_email(to, f"[Alerte] {subject}", html)
