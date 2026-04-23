"""Onboarding automatisé post-paiement Stripe.

Déclenché sur checkout.session.completed :
  1. Marque l'organisation active avec son plan
  2. Crée un projet démo "Mon premier projet - Immeuble Démo"
  3. Lance un 1er justificatif thermique en mode stub (valeur dès J0)
  4. Envoie un email de bienvenue avec lien vers le projet démo

L'objectif : l'utilisateur se connecte après paiement et voit déjà un résultat prêt.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


async def run_first_payment_onboarding(stripe_customer_id: str) -> dict[str, Any]:
    """Point d'entrée — orchestrateur onboarding.

    Retourne un dict avec le statut de chaque étape (jamais raise, fail-soft).
    """
    from app.database import get_supabase_admin

    admin = get_supabase_admin()
    result: dict[str, Any] = {
        "customer_id": stripe_customer_id,
        "org_activated": False,
        "demo_project_created": False,
        "first_task_enqueued": False,
        "welcome_email_sent": False,
    }

    # 1. Trouver l'organisation liée au customer Stripe
    org_query = admin.table("organizations").select("*").eq(
        "stripe_customer_id", stripe_customer_id,
    ).maybe_single().execute()
    if not org_query.data:
        logger.warning("Organisation introuvable pour customer %s", stripe_customer_id)
        result["error"] = "organization_not_found"
        return result

    org = org_query.data
    org_id = org["id"]

    # 2. Idempotence : si l'onboarding a déjà tourné, on skip
    if org.get("onboarded_at"):
        logger.info("Organisation %s déjà onboardée le %s", org_id, org["onboarded_at"])
        result["already_onboarded"] = True
        return result

    # 3. Marquer active
    try:
        admin.table("organizations").update({
            "active": True,
            "onboarded_at": datetime.utcnow().isoformat(),
        }).eq("id", org_id).execute()
        result["org_activated"] = True
    except Exception as e:
        logger.warning("Activation org échouée : %s", e)

    # 4. Créer le projet démo
    demo_project_id = None
    try:
        canton = org.get("canton") or "GE"
        project_data = {
            "id": str(uuid.uuid4()),
            "organization_id": org_id,
            "name": "Mon premier projet - Immeuble Démo",
            "description": (
                f"Projet de démonstration créé automatiquement lors de l'activation de votre compte. "
                f"Immeuble logement collectif à {'Genève' if canton == 'GE' else canton}, "
                f"neuf, 1250 m² SRE, 18 logements."
            ),
            "address": "Rue de la Démonstration 1",
            "canton": canton,
            "commune": "Genève" if canton == "GE" else "Lausanne",
            "affectation": "logement_collectif",
            "operation_type": "neuf",
            "sre_m2": 1250,
            "standard_energetique": "sia_380_1",
            "phase_sia": "31_avant_projet",
            "created_at": datetime.utcnow().isoformat(),
        }
        admin.table("projects").insert(project_data).execute()
        demo_project_id = project_data["id"]
        result["demo_project_created"] = True
        result["demo_project_id"] = demo_project_id
    except Exception as e:
        logger.warning("Création projet démo échouée : %s", e)

    # 5. Lancer une 1re tâche stub pour remplir le dashboard avec un résultat
    if demo_project_id:
        try:
            task_id = str(uuid.uuid4())
            admin.table("tasks").insert({
                "id": task_id,
                "organization_id": org_id,
                "project_id": demo_project_id,
                "task_type": "simulation_energetique_rapide",
                "status": "queued",
                "input_params": {
                    "project_name": "Mon premier projet - Immeuble Démo",
                    "programme": {
                        "canton": canton,
                        "affectation": "logement_collectif",
                        "sre_m2": 1250,
                        "standard": "sia_380_1_neuf",
                        "heating_vector": "chauffage_distance",
                        "facteur_forme": "standard",
                        "nb_etages": 4,
                        "nb_logements": 18,
                    },
                    "author": "BET Agent - Onboarding",
                },
                "attempts": 0,
                "created_at": datetime.utcnow().isoformat(),
            }).execute()

            # Enqueue
            try:
                from arq.connections import create_pool, RedisSettings
                from app.config import settings
                pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
                await pool.enqueue_job("run_task", task_id)
                await pool.close()
                result["first_task_enqueued"] = True
                result["first_task_id"] = task_id
            except Exception as enq_err:
                logger.warning("Enqueue 1re tâche échoué (reste en queued DB) : %s", enq_err)
                result["first_task_enqueued"] = False
        except Exception as e:
            logger.warning("Création 1re tâche échouée : %s", e)

    # 6. Email de bienvenue
    try:
        from app.services.email_service import send_welcome_email
        send_welcome_email(
            to=[org["email"]],
            organization_name=org["name"],
            canton=org.get("canton") or "GE",
            plan=org.get("plan") or "starter",
            demo_project_id=demo_project_id,
        )
        result["welcome_email_sent"] = True
    except Exception as e:
        logger.warning("Email bienvenue échoué : %s", e)

    logger.info("Onboarding org=%s terminé : %s", org_id, result)
    return result
