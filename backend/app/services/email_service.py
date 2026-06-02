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


def send_approval_request_email(
    to: list[str],
    task_type: str,
    project_name: str,
    confidence_score: int,
    confidence_level: str,
    alerts: list[str],
    approve_token: str,
    reject_token: str,
    backend_url: str = "",
) -> Optional[str]:
    """Levier 3 — Email d'approbation 1-clic.

    L'ingénieur reçoit un résumé court (score + points à vérifier) et deux
    boutons qui approuvent/rejettent sans qu'il ait à se connecter.
    """
    from app.config import settings as _settings
    base = backend_url or _settings.BACKEND_URL

    task_labels = {
        "redaction_cctp": "CCTP",
        "justificatif_sia_380_1": "Justificatif thermique SIA 380/1",
        "note_calcul_sia_260_267": "Note de calcul structure",
        "chiffrage_dpgf": "DPGF",
        "aeai_rapport": "Rapport AEAI",
        "idc_geneve_rapport": "Rapport IDC",
    }
    label = task_labels.get(task_type, task_type.replace("_", " ").title())

    # Couleur selon le niveau de confiance
    color = {"high": "#16a34a", "medium": "#d97706", "low": "#dc2626"}.get(confidence_level, "#525252")
    level_fr = {"high": "élevée", "medium": "moyenne", "low": "faible"}.get(confidence_level, confidence_level)

    approve_url = f"{base}/api/tasks/approve-via-token?token={approve_token}"
    reject_url = f"{base}/api/tasks/approve-via-token?token={reject_token}"

    alerts_html = ""
    if alerts:
        items = "".join(f"<li style='margin:4px 0;color:#525252;'>{a}</li>" for a in alerts[:6])
        alerts_html = f"""
        <div style="margin:16px 0;padding:12px 16px;background:#fef3c7;border-radius:8px;">
          <p style="margin:0 0 8px;font-weight:600;font-size:14px;color:#92400e;">Points à vérifier ({len(alerts)})</p>
          <ul style="margin:0;padding-left:18px;font-size:13px;">{items}</ul>
        </div>
        """
    else:
        alerts_html = """
        <div style="margin:16px 0;padding:12px 16px;background:#dcfce7;border-radius:8px;">
          <p style="margin:0;font-size:14px;color:#166534;">Aucun point bloquant signalé par l'agent.</p>
        </div>
        """

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color:#0a0a0a;">
      <h2 style="margin:0 0 4px;font-size:20px;font-weight:600;">Document à valider : {label}</h2>
      <p style="margin:0 0 16px;color:#525252;font-size:14px;">Projet : <strong>{project_name}</strong></p>

      <div style="display:inline-block;padding:6px 14px;border-radius:99px;background:{color}1a;margin-bottom:8px;">
        <span style="color:{color};font-weight:600;font-size:14px;">Confiance {level_fr} — {confidence_score}%</span>
      </div>

      {alerts_html}

      <div style="margin:24px 0;">
        <a href="{approve_url}" style="display:inline-block;padding:12px 28px;background:#16a34a;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;margin-right:12px;">✓ Approuver</a>
        <a href="{reject_url}" style="display:inline-block;padding:12px 28px;background:#fff;color:#dc2626;text-decoration:none;border:1px solid #dc2626;border-radius:8px;font-weight:600;font-size:15px;">Renvoyer</a>
      </div>

      <p style="margin:16px 0 0;color:#a3a3a3;font-size:12px;">
        En approuvant, vous engagez votre validation professionnelle sur ce document.
        Lien valable 72h. Vous pouvez aussi ouvrir le document complet dans votre espace BET Agent.
      </p>
    </div>
    """
    return send_email(to, f"[À valider] {label} — {project_name}", html)


def send_alert_email(to: list[str], subject: str, body_html: str) -> Optional[str]:
    """Email d'alerte (réglementaire, incident)."""
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; padding: 24px;">
      <h2 style="margin: 0 0 16px; font-size: 20px; font-weight: 600; color: #b45309;">⚠ Alerte</h2>
      {body_html}
    </div>
    """
    return send_email(to, f"[Alerte] {subject}", html)


def send_welcome_email(
    to: list[str],
    organization_name: str,
    canton: str = "GE",
    plan: str = "starter",
    demo_project_id: Optional[str] = None,
) -> Optional[str]:
    """Email de bienvenue après activation d'un plan payant."""
    from app.config import settings

    base_url = settings.FRONTEND_URL.rstrip("/")
    demo_link = f"{base_url}/projects/{demo_project_id}" if demo_project_id else f"{base_url}/dashboard"

    plan_labels = {"starter": "Starter (490 CHF/mois)", "pro": "Pro (1 900 CHF/mois)", "enterprise": "Enterprise"}
    plan_label = plan_labels.get(plan, plan.capitalize())

    body_html = f"""
<div style="font-family:-apple-system,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a;">
  <h1 style="font-size:22px;font-weight:500;margin:0 0 16px;">Bienvenue chez BET Agent</h1>
  <p style="line-height:1.6;">Bonjour,</p>
  <p style="line-height:1.6;">
    Votre compte <strong>{organization_name}</strong> est maintenant actif avec le plan <strong>{plan_label}</strong>.
    Pour vous faire gagner du temps, nous avons créé un projet de démonstration dans votre espace avec
    une simulation énergétique déjà lancée.
  </p>

  <div style="margin:24px 0;padding:16px;background:#f5f5f4;border-radius:8px;">
    <p style="margin:0 0 8px;font-weight:500;">Projet démo : Immeuble logement collectif</p>
    <p style="margin:0;color:#666;font-size:14px;">
      Canton : {canton} · SRE 1250 m² · 18 logements · Standard SIA 380/1 neuf
    </p>
  </div>

  <div style="margin:24px 0;">
    <a href="{demo_link}"
       style="display:inline-block;padding:12px 20px;background:#111;color:#fff;text-decoration:none;border-radius:6px;font-weight:500;">
      Accéder au projet démo
    </a>
  </div>

  <h2 style="font-size:16px;font-weight:500;margin:32px 0 12px;">Les 6 modules disponibles</h2>
  <ul style="line-height:1.8;color:#333;padding-left:20px;">
    <li>Thermique SIA 380/1 — justificatifs et gbXML pour Lesosai</li>
    <li>Structure SIA 260-267 — SAF pour Scia/RFEM + double-check</li>
    <li>IDC Genève — extraction factures + formulaire OCEN</li>
    <li>AEAI incendie — checklists par typologie + rapport</li>
    <li>Dossier mise en enquête — APA/APC + mémoire justificatif</li>
    <li>Veille réglementaire — Fedlex + 6 cantons romands</li>
  </ul>

  <p style="line-height:1.6;margin-top:32px;">
    Une question ? Répondez simplement à cet email.<br>
    À très vite,<br>
    L'équipe BET Agent
  </p>

  <p style="font-size:12px;color:#999;border-top:0.5px solid #ddd;padding-top:16px;margin-top:32px;">
    BET Agent · Lausanne · <a href="{base_url}" style="color:#666;">bet-agent.ch</a>
  </p>
</div>
"""
    return send_email(
        to=to,
        subject="Bienvenue chez BET Agent — votre projet démo est prêt",
        body_html=body_html,
    )
