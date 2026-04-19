"""Agent veille réglementaire romande."""
import json
import logging
from datetime import datetime

from app.agent.router import call_llm
from app.agent.swiss.prompts_ch import get_prompt_ch
from app.database import get_supabase_admin
from app.services.swiss.cantonal_feeds import daily_cantonal_veille
from app.services.swiss.fedlex import daily_fedlex_veille

logger = logging.getLogger(__name__)


async def run_veille_romande() -> dict:
    """Run complet : Fedlex + 5 cantons romands + analyse LLM + insert DB + envoi alertes."""
    # 1. Collecte
    fedlex_items = await daily_fedlex_veille()
    cantonal_items = await daily_cantonal_veille(["GE", "VD", "NE", "FR", "VS", "JU"])

    all_items = []
    for item in fedlex_items:
        item["source"] = "Fedlex"
        item["jurisdiction"] = ["CH"]
        all_items.append(item)
    for canton, items in cantonal_items.items():
        for item in items:
            item["source"] = f"Canton-{canton}"
            item["jurisdiction"] = [f"CH-{canton}"]
            all_items.append(item)

    if not all_items:
        logger.info("Veille CH : aucun nouvel élément détecté")
        return {"new_alerts": 0, "critical": 0, "skipped": True}

    # 2. Analyse LLM
    system = get_prompt_ch("veille_romande")

    # Limite la taille du prompt
    items_serialized = json.dumps(all_items[:40], ensure_ascii=False, indent=2)

    user_content = f"""Analyser les publications réglementaires suivantes et produire le JSON d'alertes demandé.

{items_serialized}"""

    llm_result = await call_llm(
        task_type="veille_reglementaire",  # Haiku
        system_prompt=system,
        user_content=user_content,
        max_tokens=4000,
        temperature=0.1,
    )

    # Parse
    raw = llm_result["text"].strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1]) if raw.endswith("```") else "\n".join(raw.split("\n")[1:])
    start, end = raw.find("{"), raw.rfind("}")

    parsed = {"alerts": [], "summary_md": ""}
    if start != -1 and end != -1:
        try:
            parsed = json.loads(raw[start:end + 1])
        except json.JSONDecodeError as e:
            logger.error(f"Parse veille échec : {e}")

    # 3. Insert DB
    admin = get_supabase_admin()
    critical_alerts = []
    inserted = 0
    for alert in parsed.get("alerts", []):
        try:
            admin.table("regulatory_changes").insert({
                "change_type": "published",
                "impact_level": alert.get("level", "INFO"),
                "impact_summary": alert.get("impact", "")[:2000],
                "affected_project_types": alert.get("affected_project_types", []),
                "source_url": alert.get("url"),
                "raw_data": alert,
            }).execute()
            inserted += 1
            if alert.get("level") == "CRITIQUE":
                critical_alerts.append(alert)
        except Exception as e:
            logger.warning(f"Insert alerte échec : {e}")

    # 4. Envoi email pour alertes critiques
    if critical_alerts:
        try:
            from app.config import settings
            from app.services.email_service import send_alert_email
            orgs = admin.table("organizations").select("id,email,name,canton").eq("active", True).execute()

            for org in orgs.data or []:
                # On ne notifie que les orgs dont le canton est concerné
                org_canton = org.get("canton")
                relevant = [a for a in critical_alerts
                            if "CH" in (a.get("jurisdiction") or [])
                               or (org_canton and f"CH-{org_canton}" in (a.get("jurisdiction") or []))]
                if not relevant:
                    continue

                body = "<ul>" + "".join(
                    f"<li><strong>{a.get('title', '')}</strong> ({', '.join(a.get('jurisdiction', []))})<br>"
                    f"<span style='color:#737373'>{a.get('impact', '')}</span><br>"
                    f"<a href='{a.get('url', '#')}'>Lire la source</a></li>"
                    for a in relevant
                ) + "</ul>"
                send_alert_email(
                    to=[org["email"]],
                    subject=f"Nouvelles normes CRITIQUES ({len(relevant)})",
                    body_html=body,
                )
        except Exception as e:
            logger.error(f"Envoi emails critiques échec : {e}")

    return {
        "new_alerts": inserted,
        "critical": len(critical_alerts),
        "summary_md": parsed.get("summary_md", ""),
        "items_analyzed": len(all_items),
    }
