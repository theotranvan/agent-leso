"""Routage intelligent des modèles Claude selon la complexité et l'enjeu de chaque tâche.

Principes de classification
===========================

1. **Haiku (80% de volume)** — tâches où la structure est fixe et la valeur
   provient de la vitesse et du coût faible. Checklist, extraction, classification,
   génération depuis template, résumés. Le LLM sert de "colle intelligente".

2. **Sonnet (18% de volume)** — tâches où la QUALITÉ DE RÉDACTION et le raisonnement
   multi-contexte comptent. Rapports narratifs, rédaction CCTP, synthèse de plusieurs
   documents, réponse argumentée à observations. L'ingénieur signataire attend
   un niveau "collègue expérimenté" — pas juste une structure correcte.

3. **Opus (2% de volume)** — uniquement quand le livrable engage la responsabilité
   professionnelle ET que l'agent a un contexte riche à synthétiser :
   - Note de calcul structure SIA 260-267 (signature ingénieur engagée)
   - Justificatif SIA 380/1 (signature thermicien engagée)
   - Dossier mise en enquête (responsabilité architecte + BET)

   PAS Opus pour juste "structurer des données calculées ailleurs" — la valeur
   d'Opus est sa rigueur de raisonnement, pas sa capacité à remplir un template.

Fallback
========
Opus → Sonnet si échec réseau ou rate limit (les 2% Opus ont toujours un plan B).
Sonnet → Haiku jamais automatique (qualité trop différente, vaut mieux une erreur).

Context
=======
ContextVar `_current_task_ctx` : défini par l'orchestrateur avant le dispatch,
consulté automatiquement par `call_llm()` pour :
  - Associer chaque appel LLM à organization_id + task_id (pour token_usage)
  - Détecter si c'est une régénération (is_regeneration flag)
  - Récupérer les motifs de régénération pour logging

Cela évite d'avoir à passer ces arguments à travers chaque agent.
"""
from __future__ import annotations

import logging
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

from anthropic import APIError, AsyncAnthropic, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """Contexte d'exécution d'une tâche, propagé via ContextVar."""

    organization_id: str
    task_id: str
    task_type: str
    is_regeneration: bool = False
    regeneration_attempt: int = 0
    regeneration_reasons: Optional[list[str]] = None
    regeneration_sections: Optional[list[str]] = None


_current_task_ctx: ContextVar[Optional[TaskContext]] = ContextVar(
    "_current_task_ctx", default=None,
)


def set_task_context(ctx: Optional[TaskContext]) -> None:
    """Défini le contexte courant. Appelé par l'orchestrateur."""
    _current_task_ctx.set(ctx)


def get_task_context() -> Optional[TaskContext]:
    """Retourne le contexte courant ou None."""
    return _current_task_ctx.get()


# Modèles
MODEL_OPUS = "claude-opus-4-6"
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_HAIKU = "claude-haiku-4-5-20251001"


# ==========================================================================
# ROUTING TABLE REPENSÉE — justification par tâche
# ==========================================================================

ROUTING_TABLE: dict[str, str] = {
    # --------------------------------------------------------------------
    # OPUS — responsabilité professionnelle engagée + synthèse complexe
    # --------------------------------------------------------------------
    # Note de calcul structure : l'ingénieur signe sous sa responsabilité civile.
    # Synthèse SAF + double-check + argumentation SIA 260-267. Enjeu majeur.
    "note_calcul_sia_260_267": MODEL_OPUS,
    "note_calcul_structure": MODEL_OPUS,        # V1 France équivalent

    # Justificatif énergétique : thermicien signataire. Raisonnement sur les
    # hypothèses, la station climatique, les limites, la stratégie d'enveloppe.
    "justificatif_sia_380_1": MODEL_OPUS,
    "calcul_thermique_re2020": MODEL_OPUS,      # V1 France équivalent

    # Dossier mise en enquête : document de ~20 pages qui engage le BET.
    # Argumentation juridico-technique, liaison entre 10 domaines (énergie,
    # incendie, LDTR, stationnement...). Opus justifie sa rigueur.
    "dossier_mise_enquete": MODEL_OPUS,

    # --------------------------------------------------------------------
    # SONNET — qualité de rédaction et raisonnement multi-contexte
    # --------------------------------------------------------------------
    # CCTP : prescriptif détaillé, 1500+ mots structurés. Qualité texte cruciale.
    "redaction_cctp": MODEL_SONNET,
    "descriptif_can_sia_451": MODEL_SONNET,

    # Mémoire technique, compte-rendu élaboré : qualité narrative importante.
    "memoire_technique": MODEL_SONNET,
    "compte_rendu_reunion": MODEL_SONNET,  # réhaussé : un CR mal rédigé
                                           # = ingénieur doit tout réécrire

    # Rapports narratifs contextualisés
    "idc_geneve_rapport": MODEL_SONNET,
    "aeai_rapport": MODEL_SONNET,
    "controle_reglementaire_geneve": MODEL_SONNET,
    "controle_reglementaire_vaud": MODEL_SONNET,
    "controle_reglementaire_canton": MODEL_SONNET,

    # Réponse aux observations : argumentation juridique point par point.
    # Impact direct sur la décision de l'autorité.
    "reponse_observations_autorite": MODEL_SONNET,

    # Chiffrage : tableaux + raisonnement sur les quantités + rédaction des
    # désignations. Sonnet suffit.
    "chiffrage_dpgf": MODEL_SONNET,
    "chiffrage_dqe": MODEL_SONNET,

    # Coordination multi-lots : raisonnement transversal requis
    "coordination_inter_lots": MODEL_SONNET,
    "dossier_permis_construire": MODEL_SONNET,

    # DOE : compilation argumentée avec synthèse des fiches techniques
    "doe_compilation": MODEL_SONNET,

    # Pré-BIM depuis texte : extraction structurée à faible enjeu mais on attend
    # une bonne compréhension d'un programme architectural en langage naturel.
    "prebim_generation": MODEL_SONNET,
    "prebim_extraction": MODEL_SONNET,

    # Analyse IFC détaillée
    "analyse_ifc": MODEL_SONNET,

    # Vérification eurocode (France) : raisonnement technique structuré
    "verification_eurocode": MODEL_SONNET,  # rétrogradé d'Opus : le calcul
                                             # officiel reste dans le logiciel
                                             # structure. L'agent synthétise.

    # --------------------------------------------------------------------
    # HAIKU — tâches où structure prime sur raisonnement
    # --------------------------------------------------------------------
    # Veille : classification thématique + extraction métadonnées
    "veille_reglementaire": MODEL_HAIKU,
    "veille_romande": MODEL_HAIKU,
    "alerte_norme": MODEL_HAIKU,

    # Résumés, notifications — Haiku est littéralement fait pour ça
    "resume_document": MODEL_HAIKU,
    "email_notification": MODEL_HAIKU,
    "extraction_metadata": MODEL_HAIKU,

    # Extraction factures IDC : structure fixe (valeur/unité/période),
    # Haiku + Vision suffisent.
    "idc_extraction_facture": MODEL_HAIKU,

    # Checklists AEAI enrichies : adaptation d'un template existant au contexte
    "aeai_checklist_generation": MODEL_HAIKU,

    # Calcul CECB : c'est essentiellement un parser + assembleur de rapport
    # depuis résultats officiels Lesosai. Pas besoin d'Opus.
    "calcul_cecb": MODEL_HAIKU,

    # Simulation rapide et métrés : 100% déterministe, pas d'appel LLM réel,
    # mais taggés pour traçabilité quota
    "simulation_energetique_rapide": MODEL_HAIKU,
    "metres_automatiques_ifc": MODEL_HAIKU,

    # Calcul acoustique France : retrograde d'Opus car on exploite un logiciel
    # externe, l'agent ne fait que rédiger la synthèse
    "calcul_acoustique": MODEL_HAIKU,
}


# Tâches "déterministes" — flag pour éviter d'enregistrer un coût LLM factice
DETERMINISTIC_TASKS: frozenset[str] = frozenset({
    "simulation_energetique_rapide",
    "metres_automatiques_ifc",
})


# Tarifs API Anthropic (USD / million de tokens)
MODEL_PRICING_USD = {
    MODEL_OPUS: {"input": 15.0, "output": 75.0},
    MODEL_SONNET: {"input": 3.0, "output": 15.0},
    MODEL_HAIKU: {"input": 0.80, "output": 4.0},
}

# Conversions
USD_TO_EUR = 0.92
USD_TO_CHF = 0.88

_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def get_model_for_task(task_type: str, *, override: Optional[str] = None) -> str:
    """Retourne le modèle Claude à utiliser pour un type de tâche.

    `override` permet de forcer un modèle (usage : régénération où on peut
    upgrade vers Sonnet si Haiku a échoué).
    """
    if override in (MODEL_OPUS, MODEL_SONNET, MODEL_HAIKU):
        return override
    return ROUTING_TABLE.get(task_type, MODEL_SONNET)


def is_deterministic_task(task_type: str) -> bool:
    return task_type in DETERMINISTIC_TASKS


def estimate_cost_eur(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estime le coût en euros d'un appel LLM."""
    pricing = MODEL_PRICING_USD.get(model, MODEL_PRICING_USD[MODEL_SONNET])
    cost_usd = (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]
    return round(cost_usd * USD_TO_EUR, 4)


def estimate_cost_chf(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estime le coût en CHF d'un appel LLM (utilisé pour facturation et quota)."""
    pricing = MODEL_PRICING_USD.get(model, MODEL_PRICING_USD[MODEL_SONNET])
    cost_usd = (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]
    return round(cost_usd * USD_TO_CHF, 4)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=1, max=10),
    retry=retry_if_exception_type((APIError, RateLimitError)),
    reraise=True,
)
async def _call_anthropic(
    model: str,
    system: str,
    user_content: str | list,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> tuple[str, dict]:
    """Appel bas niveau avec retry exponentiel."""
    messages = [{"role": "user", "content": user_content}]

    response = await _client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=messages,
    )

    text_parts = [block.text for block in response.content if hasattr(block, "text")]
    text = "\n".join(text_parts)

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return text, usage


async def call_llm(
    task_type: str,
    system_prompt: str,
    user_content: str | list,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    allow_fallback: bool = True,
    model_override: Optional[str] = None,
    organization_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> dict:
    """Appelle le LLM approprié pour une tâche, avec fallback Opus → Sonnet.

    Retourne: {text, model, tokens_used, input_tokens, output_tokens,
               cost_eur, cost_chf, fallback_used}

    Fallback automatique depuis le TaskContext si `organization_id` et `task_id`
    ne sont pas fournis explicitement. Cela évite que les agents oublient ces
    arguments (non-logging silencieux = anti-pattern).
    """
    # Fallback sur le contexte courant défini par l'orchestrateur
    ctx = get_task_context()
    if organization_id is None and ctx is not None:
        organization_id = ctx.organization_id
    if task_id is None and ctx is not None:
        task_id = ctx.task_id

    primary_model = get_model_for_task(task_type, override=model_override)
    fallback_used = False

    try:
        text, usage = await _call_anthropic(
            primary_model, system_prompt, user_content, max_tokens, temperature,
        )
        model_final = primary_model
    except Exception as e:
        logger.error("Appel %s échoué après retries : %s", primary_model, e)
        if allow_fallback and primary_model == MODEL_OPUS:
            logger.warning("Fallback Opus → Sonnet pour task_type=%s", task_type)
            text, usage = await _call_anthropic(
                MODEL_SONNET, system_prompt, user_content, max_tokens, temperature,
            )
            model_final = MODEL_SONNET
            fallback_used = True
            try:
                from app.services.email_service import send_alert_email
                send_alert_email(
                    to=[settings.ADMIN_EMAIL],
                    subject=f"Fallback LLM Opus → Sonnet (task={task_type})",
                    body_html=(
                        f"<p>Modèle Opus a échoué pour tâche <strong>{task_type}</strong>. "
                        f"Fallback Sonnet utilisé.</p><p>Erreur : {e}</p>"
                    ),
                )
            except Exception:
                pass
        else:
            raise

    total_tokens = usage["input_tokens"] + usage["output_tokens"]
    cost_eur = estimate_cost_eur(model_final, usage["input_tokens"], usage["output_tokens"])
    cost_chf = estimate_cost_chf(model_final, usage["input_tokens"], usage["output_tokens"])

    logger.info(
        "LLM call: task=%s model=%s in=%d out=%d cost_chf=%.4f fallback=%s",
        task_type, model_final, usage["input_tokens"], usage["output_tokens"],
        cost_chf, fallback_used,
    )

    # Log token_usage si organization fournie
    if organization_id:
        try:
            from app.services.token_quota import log_token_usage
            # Récupère flags de régénération depuis le contexte si dispo
            is_regen = False
            regen_reason = None
            regen_sections = None
            regen_attempt = 0
            if ctx is not None:
                is_regen = ctx.is_regeneration
                regen_attempt = ctx.regeneration_attempt
                if ctx.regeneration_reasons:
                    regen_reason = ",".join(ctx.regeneration_reasons)
                regen_sections = ctx.regeneration_sections

            await log_token_usage(
                organization_id=organization_id,
                task_id=task_id,
                task_type=task_type,
                model=model_final,
                tokens_in=usage["input_tokens"],
                tokens_out=usage["output_tokens"],
                cost_chf=cost_chf,
                fallback_used=fallback_used,
                is_regeneration=is_regen,
                regeneration_reason=regen_reason,
                regeneration_sections=regen_sections,
                regeneration_attempt=regen_attempt,
            )
        except Exception as exc:
            logger.warning("log_token_usage échoué : %s", exc)

    return {
        "text": text,
        "model": model_final,
        "tokens_used": total_tokens,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cost_eur": cost_eur,
        "cost_chf": cost_chf,
        "fallback_used": fallback_used,
    }
