"""Routage des modèles Claude selon le type de tâche.

Règle : Opus = critique (5%), Sonnet = standard (75%), Haiku = léger (20%).
Fallback : si Opus échoue 2x → retry Sonnet + log alerte.
"""
import logging
from typing import Optional

from anthropic import APIError, AsyncAnthropic, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

MODEL_OPUS = "claude-opus-4-6"
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_HAIKU = "claude-haiku-4-5-20251001"

ROUTING_TABLE: dict[str, str] = {
    # Opus 4.6 - calculs critiques
    "note_calcul_structure": MODEL_OPUS,
    "verification_eurocode": MODEL_OPUS,
    "calcul_thermique_re2020": MODEL_OPUS,
    "calcul_acoustique": MODEL_OPUS,

    # Sonnet 4.6 - tâches standard
    "redaction_cctp": MODEL_SONNET,
    "memoire_technique": MODEL_SONNET,
    "chiffrage_dpgf": MODEL_SONNET,
    "chiffrage_dqe": MODEL_SONNET,
    "coordination_inter_lots": MODEL_SONNET,
    "dossier_permis_construire": MODEL_SONNET,
    "analyse_ifc": MODEL_SONNET,
    "doe_compilation": MODEL_SONNET,

    # Haiku 4.5 - tâches légères
    "veille_reglementaire": MODEL_HAIKU,
    "resume_document": MODEL_HAIKU,
    "compte_rendu_reunion": MODEL_HAIKU,
    "alerte_norme": MODEL_HAIKU,
    "email_notification": MODEL_HAIKU,
    "extraction_metadata": MODEL_HAIKU,

    # ==== V2 Suisse romande ====
    # Opus - calculs critiques CH
    "justificatif_sia_380_1": MODEL_OPUS,
    "note_calcul_sia_260_267": MODEL_OPUS,
    "calcul_cecb": MODEL_OPUS,

    # Sonnet - tâches standard CH
    "descriptif_can_sia_451": MODEL_SONNET,
    "controle_reglementaire_geneve": MODEL_SONNET,
    "controle_reglementaire_vaud": MODEL_SONNET,
    "controle_reglementaire_canton": MODEL_SONNET,
    "prebim_generation": MODEL_SONNET,
    "prebim_extraction": MODEL_SONNET,
    "dossier_mise_enquete": MODEL_SONNET,
    "idc_geneve_rapport": MODEL_SONNET,
    "aeai_rapport": MODEL_SONNET,

    # Haiku - CH léger
    "idc_extraction_facture": MODEL_HAIKU,
    "veille_romande": MODEL_HAIKU,
    "aeai_checklist_generation": MODEL_HAIKU,
}

# Tarifs API Anthropic (USD / million de tokens) - pour estimation de coût
MODEL_PRICING = {
    MODEL_OPUS: {"input": 15.0, "output": 75.0},
    MODEL_SONNET: {"input": 3.0, "output": 15.0},
    MODEL_HAIKU: {"input": 0.80, "output": 4.0},
}

EUR_PER_USD = 0.92

_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def get_model_for_task(task_type: str) -> str:
    """Retourne le modèle Claude à utiliser pour un type de tâche."""
    return ROUTING_TABLE.get(task_type, MODEL_SONNET)


def estimate_cost_eur(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estime le coût en euros d'un appel LLM."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING[MODEL_SONNET])
    cost_usd = (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]
    return round(cost_usd * EUR_PER_USD, 4)


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
) -> dict:
    """Appelle le LLM approprié pour une tâche, avec fallback Opus → Sonnet.

    Retourne: {text, model, tokens_used, cost_eur, fallback_used}
    """
    primary_model = get_model_for_task(task_type)
    fallback_used = False

    try:
        text, usage = await _call_anthropic(primary_model, system_prompt, user_content, max_tokens, temperature)
        model_final = primary_model
    except Exception as e:
        logger.error(f"Appel {primary_model} échoué après retries: {e}")
        if allow_fallback and primary_model == MODEL_OPUS:
            logger.warning(f"Fallback Opus → Sonnet pour task_type={task_type}")
            text, usage = await _call_anthropic(MODEL_SONNET, system_prompt, user_content, max_tokens, temperature)
            model_final = MODEL_SONNET
            fallback_used = True
            # Alerte admin (via email async, non bloquant)
            try:
                from app.services.email_service import send_alert_email
                send_alert_email(
                    to=[settings.ADMIN_EMAIL],
                    subject=f"Fallback LLM Opus → Sonnet (task={task_type})",
                    body_html=f"<p>Le modèle Opus a échoué pour la tâche <strong>{task_type}</strong>. Fallback Sonnet utilisé.</p><p>Erreur : {e}</p>",
                )
            except Exception:
                pass
        else:
            raise

    total_tokens = usage["input_tokens"] + usage["output_tokens"]
    cost = estimate_cost_eur(model_final, usage["input_tokens"], usage["output_tokens"])

    logger.info(
        f"LLM call: task={task_type} model={model_final} in={usage['input_tokens']} out={usage['output_tokens']} "
        f"cost={cost}€ fallback={fallback_used}"
    )

    return {
        "text": text,
        "model": model_final,
        "tokens_used": total_tokens,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "cost_eur": cost,
        "fallback_used": fallback_used,
    }
