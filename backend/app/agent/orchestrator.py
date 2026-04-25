"""Orchestrateur : exécute une tâche en dispatchant vers le bon module."""
import logging
from datetime import datetime
from typing import Any

from app.database import get_supabase_admin

logger = logging.getLogger(__name__)


async def execute_task(task_id: str) -> dict[str, Any]:
    """Point d'entrée unique pour exécuter une tâche.

    - Lit la tâche depuis la DB
    - Route vers le module approprié
    - Met à jour le statut, le résultat, les coûts
    - Envoie l'email si demandé
    - Gère les erreurs et les retries
    """
    admin = get_supabase_admin()

    task_result = admin.table("tasks").select("*").eq("id", task_id).maybe_single().execute()
    if not task_result.data:
        logger.error(f"Tâche {task_id} introuvable")
        return {"status": "failed", "error": "Tâche introuvable"}

    task = task_result.data

    # Passe en running
    admin.table("tasks").update({
        "status": "running",
        "attempts": task.get("attempts", 0) + 1,
    }).eq("id", task_id).execute()

    task_type = task["task_type"]

    # ==================== QUOTA CHECK (V5) ====================
    # Vérifie que l'organisation a encore des tokens avant tout dispatch.
    # Si dépassé → passe la tâche en 'failed' avec un message utilisateur clair.
    try:
        from app.services.token_quota import TokenQuotaExceeded, check_quota_available
        await check_quota_available(
            organization_id=task["organization_id"],
            estimated_tokens=0,
        )
    except TokenQuotaExceeded as quota_err:
        logger.warning(
            "Task %s bloquée : quota dépassé pour org=%s",
            task_id, task["organization_id"],
        )
        admin.table("tasks").update({
            "status": "failed",
            "error_message": quota_err.user_message,
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", task_id).execute()
        return {
            "status": "failed",
            "error": "quota_exceeded",
            "user_message": quota_err.user_message,
            "tokens_used": quota_err.tokens_used,
            "tokens_limit": quota_err.tokens_limit,
        }
    except Exception as exc:
        # Autre erreur de check : on log mais on n'empêche pas la tâche
        logger.warning("Check quota échec (non-bloquant) : %s", exc)

    # ==================== Ingestion documents (V4+) ====================
    # Enrichit automatiquement les input_params avec les documents du projet
    try:
        from app.agent.ingestion import ingest_for_task
        ingestion = await ingest_for_task(
            task_type=task_type,
            organization_id=task["organization_id"],
            project_id=task.get("project_id"),
            input_params=task.get("input_params") or {},
        )
        enriched_params = ingestion.merge_into(task.get("input_params") or {})
        task["input_params"] = enriched_params

        if ingestion.documents_attached:
            logger.info(
                "Ingestion task=%s : %d docs attachés, %d warnings",
                task_id, len(ingestion.documents_attached), len(ingestion.warnings),
            )
    except Exception as exc:
        logger.warning("Ingestion échec pour task %s : %s", task_id, exc)
        # Non-bloquant : continue avec input_params original

    # ==================== TaskContext (V5) ====================
    # Propage org_id / task_id / régénération à call_llm via ContextVar.
    # Les agents n'ont plus besoin de passer ces arguments explicitement.
    from app.agent.router import TaskContext, set_task_context
    regen_ctx = (task.get("input_params") or {}).get("regeneration_context") or {}
    task_context = TaskContext(
        organization_id=task["organization_id"],
        task_id=task_id,
        task_type=task_type,
        is_regeneration=bool(regen_ctx),
        regeneration_attempt=int(regen_ctx.get("attempt") or 0),
        regeneration_reasons=regen_ctx.get("reasons") or None,
        regeneration_sections=regen_ctx.get("target_sections") or None,
    )
    set_task_context(task_context)

    try:
        # Dispatch vers le module
        from app.agent.modules import cctp, chiffrage, coordination, doe, note_calcul, rapport

        # ==================== Dispatch V1 (France) ====================
        if task_type == "redaction_cctp":
            result = await cctp.execute(task)
        elif task_type in ("note_calcul_structure", "verification_eurocode",
                           "calcul_thermique_re2020", "calcul_acoustique"):
            result = await note_calcul.execute(task)
        elif task_type in ("chiffrage_dpgf", "chiffrage_dqe"):
            result = await chiffrage.execute(task)
        elif task_type == "coordination_inter_lots":
            result = await coordination.execute(task)
        elif task_type in ("compte_rendu_reunion", "memoire_technique", "resume_document"):
            result = await rapport.execute(task)
        elif task_type == "doe_compilation":
            result = await doe.execute(task)
        elif task_type in ("veille_reglementaire", "alerte_norme"):
            result = await rapport.execute_generic(task)
        elif task_type == "extraction_metadata":
            result = await rapport.execute_generic(task)

        # ==================== Dispatch V2+V3 (Suisse romande) ====================
        elif task_type in ("justificatif_sia_380_1", "calcul_cecb"):
            from app.agent.swiss import thermique_agent
            result = await thermique_agent.execute(task)
        elif task_type == "note_calcul_sia_260_267":
            from app.agent.swiss import structure_agent
            result = await structure_agent.execute(task)
        elif task_type == "descriptif_can_sia_451":
            # CAN/SIA 451 = descriptif suisse — on réutilise le module cctp avec prompt CH
            result = await cctp.execute(task)
        elif task_type in ("controle_reglementaire_geneve",
                           "controle_reglementaire_vaud",
                           "controle_reglementaire_canton"):
            from app.agent.swiss import geneva_agent
            result = await geneva_agent.execute(task)
        elif task_type in ("prebim_generation", "prebim_extraction"):
            from app.agent.swiss import prebim_agent
            result = await prebim_agent.execute(task)
        elif task_type == "idc_geneve_rapport":
            from app.agent.swiss import idc_agent
            result = await idc_agent.execute(task)
        elif task_type == "idc_extraction_facture":
            from app.agent.swiss import idc_agent
            result = await idc_agent.execute_extraction(task)
        elif task_type == "aeai_rapport":
            from app.agent.swiss import aeai_agent
            result = await aeai_agent.execute(task)
        elif task_type == "aeai_checklist_generation":
            from app.agent.swiss import aeai_agent
            result = await aeai_agent.execute_checklist(task)
        elif task_type == "veille_romande":
            from app.agent.swiss import veille_agent
            result = await veille_agent.execute(task)
        elif task_type == "dossier_mise_enquete":
            from app.agent.swiss import dossier_enquete_agent
            result = await dossier_enquete_agent.execute(task)
        elif task_type == "reponse_observations_autorite":
            from app.agent.swiss import observations_agent
            result = await observations_agent.execute(task)
        elif task_type == "simulation_energetique_rapide":
            from app.agent.swiss import simulation_rapide_agent
            result = await simulation_rapide_agent.execute(task)
        elif task_type == "metres_automatiques_ifc":
            from app.agent.swiss import metres_agent
            result = await metres_agent.execute(task)

        else:
            raise ValueError(f"Type de tâche non supporté: {task_type}")

        # Marque completed
        admin.table("tasks").update({
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "result_url": result.get("result_url"),
            "result_preview": result.get("preview"),
            "model_used": result.get("model"),
            "tokens_used": result.get("tokens_used", 0),
            "cost_euros": result.get("cost_eur", 0),
        }).eq("id", task_id).execute()

        # Incrémente compteur tâches de l'organisation
        org = admin.table("organizations").select("tasks_used_this_month").eq("id", task["organization_id"]).maybe_single().execute()
        if org.data:
            admin.table("organizations").update({
                "tasks_used_this_month": (org.data.get("tasks_used_this_month") or 0) + 1,
            }).eq("id", task["organization_id"]).execute()

        # Audit log
        admin.table("audit_logs").insert({
            "organization_id": task["organization_id"],
            "user_id": task.get("user_id"),
            "action": "task_completed",
            "resource_type": "task",
            "resource_id": task_id,
            "metadata": {"task_type": task_type, "model": result.get("model"), "cost_eur": result.get("cost_eur")},
        }).execute()

        # Envoi email si demandé
        input_params = task.get("input_params") or {}
        if input_params.get("send_email") and input_params.get("recipient_emails") and result.get("email_bytes"):
            from app.services.email_service import send_task_completed_email
            project_name = input_params.get("project_name", "")
            if not project_name and task.get("project_id"):
                proj = admin.table("projects").select("name").eq("id", task["project_id"]).maybe_single().execute()
                if proj.data:
                    project_name = proj.data["name"]

            send_task_completed_email(
                to=input_params["recipient_emails"],
                task_type=task_type,
                project_name=project_name,
                attachment_bytes=result.get("email_bytes"),
                attachment_filename=result.get("email_filename"),
                preview_text=result.get("preview", "")[:500],
            )

        return {"status": "completed", **result}

    except Exception as e:
        logger.exception(f"Erreur exécution tâche {task_id}: {e}")
        admin.table("tasks").update({
            "status": "failed",
            "error_message": str(e)[:1000],
            "completed_at": datetime.utcnow().isoformat(),
        }).eq("id", task_id).execute()

        # Alerte admin si 3 échecs
        attempts = task.get("attempts", 0) + 1
        if attempts >= 3:
            try:
                from app.config import settings
                from app.services.email_service import send_alert_email
                send_alert_email(
                    to=[settings.ADMIN_EMAIL],
                    subject=f"Tâche {task_id} en échec définitif",
                    body_html=f"<p>Task <strong>{task_type}</strong> a échoué {attempts} fois.</p><p>Erreur : {e}</p>",
                )
            except Exception:
                pass

        return {"status": "failed", "error": str(e)}
    finally:
        # V5 : reset TaskContext pour ne pas fuiter entre tâches
        try:
            set_task_context(None)
        except Exception:
            pass
