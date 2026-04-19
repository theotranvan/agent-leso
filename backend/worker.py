"""Worker ARQ - exécution asynchrone des tâches + jobs cron."""
import logging
from datetime import datetime

from arq import cron
from arq.connections import RedisSettings

from app.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_task(ctx: dict, task_id: str) -> dict:
    """Job ARQ: exécute une tâche agent."""
    from app.agent.orchestrator import execute_task
    logger.info(f"🔧 Exécution tâche {task_id}")
    result = await execute_task(task_id)
    logger.info(f"✅ Tâche {task_id} terminée: {result.get('status')}")
    return result


async def veille_reglementaire_cron(ctx: dict) -> dict:
    """Job cron : veille Légifrance quotidienne à 06:00.

    - Cherche les nouveaux textes sur les domaines BET
    - Filtre via Haiku
    - Insère les alertes dans regulatory_alerts
    - Envoie email immédiat pour les alertes CRITIQUES
    """
    from app.agent.prompts import get_system_prompt
    from app.agent.router import call_llm
    from app.database import get_supabase_admin
    from app.services.email_service import send_alert_email
    from app.services.legifrance import daily_veille_all_domains

    logger.info("🔍 Veille réglementaire quotidienne démarrée")
    admin = get_supabase_admin()

    all_results = await daily_veille_all_domains()
    nb_inserted = 0
    critical_alerts = []

    for domain, items in all_results.items():
        if not items:
            continue

        items_text = "\n".join(
            f"- {item['title']} ({item.get('nature', '?')}, {item.get('date', '?')}) — URL: {item.get('url', '')}"
            for item in items[:20]
        )

        llm_result = await call_llm(
            task_type="veille_reglementaire",
            system_prompt=get_system_prompt("veille_reglementaire"),
            user_content=f"Analyser les textes publiés aujourd'hui dans le domaine '{domain}' :\n\n{items_text}",
            max_tokens=2048,
            temperature=0.1,
        )

        import json
        try:
            text = llm_result["text"].strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:-1])
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(text[start:end + 1])
                for alert in parsed.get("alerts", []):
                    try:
                        row = {
                            "source": "Légifrance",
                            "title": alert.get("title", "")[:500],
                            "url": alert.get("url"),
                            "content_summary": alert.get("impact", "")[:2000],
                            "affected_domains": [alert.get("domain", domain)],
                            "published_at": datetime.utcnow().isoformat(),
                        }
                        admin.table("regulatory_alerts").insert(row).execute()
                        nb_inserted += 1
                        if alert.get("level") == "CRITIQUE":
                            critical_alerts.append(alert)
                    except Exception as e:
                        logger.warning(f"Insert alerte échoué: {e}")
        except Exception as e:
            logger.error(f"Parse veille {domain} échoué: {e}")

    # Email immédiat si alertes critiques
    if critical_alerts:
        orgs = admin.table("organizations").select("id, email").eq("active", True).execute()
        for org in orgs.data or []:
            body = "<ul>" + "".join(
                f"<li><strong>{a.get('title')}</strong> — {a.get('impact')}<br><a href='{a.get('url')}'>Voir le texte</a></li>"
                for a in critical_alerts
            ) + "</ul>"
            send_alert_email(
                to=[org["email"]],
                subject=f"Nouvelles normes CRITIQUES ({len(critical_alerts)})",
                body_html=body,
            )

    logger.info(f"🔍 Veille terminée : {nb_inserted} alertes insérées, {len(critical_alerts)} critiques")
    return {"inserted": nb_inserted, "critical": len(critical_alerts)}


async def rapport_hebdo_cron(ctx: dict) -> dict:
    """Job cron : rapport hebdomadaire chaque lundi 08:00.

    Envoie un résumé des alertes de la semaine à chaque organisation active.
    """
    from app.database import get_supabase_admin
    from app.services.email_service import send_email

    logger.info("📧 Rapport hebdo démarré")
    admin = get_supabase_admin()

    from datetime import timedelta
    since = (datetime.utcnow() - timedelta(days=7)).isoformat()

    alerts = admin.table("regulatory_alerts").select("*").gte("published_at", since).order("published_at", desc=True).limit(50).execute()
    if not (alerts.data or []):
        logger.info("Pas d'alertes cette semaine")
        return {"sent": 0}

    orgs = admin.table("organizations").select("id, email, name").eq("active", True).execute()
    sent = 0
    for org in orgs.data or []:
        grouped: dict[str, list] = {}
        for a in alerts.data:
            for dom in a.get("affected_domains", []) or ["general"]:
                grouped.setdefault(dom, []).append(a)

        sections = []
        for domain, items in grouped.items():
            lis = "".join(
                f"<li><strong>{i.get('title', '')}</strong><br><span style='color:#737373'>{i.get('content_summary', '')}</span><br><a href='{i.get('url', '')}'>Lire</a></li>"
                for i in items[:10]
            )
            sections.append(f"<h3 style='margin-top:16px'>{domain.capitalize()}</h3><ul>{lis}</ul>")

        body = f"""
        <div style="font-family:-apple-system,sans-serif;max-width:700px;margin:0 auto;padding:24px;">
            <h2>Veille réglementaire — semaine du {datetime.utcnow().strftime('%d/%m/%Y')}</h2>
            <p style="color:#525252">{len(alerts.data)} nouveautés identifiées pour {org['name']}.</p>
            {''.join(sections)}
        </div>"""
        send_email(org["email"], "[BET Agent] Rapport hebdo de veille réglementaire", body)
        sent += 1

    logger.info(f"📧 Rapport hebdo envoyé à {sent} organisations")
    return {"sent": sent}


async def reset_quota_mensuel_cron(ctx: dict) -> dict:
    """Job cron : 1er du mois à 00:05 - reset des compteurs tasks_used_this_month."""
    from app.database import get_supabase_admin
    logger.info("🔄 Reset quota mensuel")
    admin = get_supabase_admin()
    # Reset global
    admin.rpc("reset_monthly_quotas").execute()
    return {"reset": True}


async def veille_romande_cron(ctx: dict) -> dict:
    """V2 - Cron veille CH romande (Fedlex + 6 cantons) à 06:30.

    Complémentaire à veille_reglementaire_cron (France Légifrance à 06:00).
    """
    from app.agent.swiss.veille_agent import run_veille_romande
    logger.info("🇨🇭 Veille romande démarrée")
    try:
        result = await run_veille_romande()
        logger.info(f"🇨🇭 Veille romande : {result}")
        return result
    except Exception as e:
        logger.exception(f"Veille romande échouée : {e}")
        return {"error": str(e)}


class WorkerSettings:
    """Configuration ARQ worker."""
    functions = [run_task]
    cron_jobs = [
        cron(veille_reglementaire_cron, hour=6, minute=0),
        cron(veille_romande_cron, hour=6, minute=30),
        cron(rapport_hebdo_cron, weekday=0, hour=8, minute=0),
        cron(reset_quota_mensuel_cron, day=1, hour=0, minute=5),
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 5
    job_timeout = 1800  # 30 min max par tâche
    keep_result = 3600
    health_check_interval = 60
