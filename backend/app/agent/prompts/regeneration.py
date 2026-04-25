"""Construction du prompt augmenté pour les régénérations ciblées.

Quand une tâche est régénérée avec du feedback, chaque agent appelle
`build_regeneration_instructions()` pour obtenir un bloc à ajouter à son
prompt utilisateur. Ce bloc liste les motifs cochés, le feedback libre,
les sections à cibler, et donne au LLM les instructions pour une
régénération CIBLÉE et NON RÉGRESSIVE (ne pas casser ce qui fonctionnait).
"""
from __future__ import annotations

from typing import Any, Optional

# Mapping des motifs vers des instructions claires pour le LLM
REASON_INSTRUCTIONS: dict[str, str] = {
    "too_generic": (
        "Le rendu précédent était trop générique. Tu dois cette fois "
        "injecter systématiquement les données spécifiques du projet "
        "(valeurs numériques, canton, typologie, affectation, adresse, etc.) "
        "au lieu de formulations réutilisables."
    ),
    "wrong_norm": (
        "La norme citée précédemment était incorrecte ou mal référencée. "
        "Vérifie soigneusement la norme applicable selon le canton et l'opération "
        "(neuf/rénovation), cite le numéro exact et le millésime, sans reproduire "
        "le texte normatif."
    ),
    "missing_info": (
        "Des informations importantes manquaient. Traite de façon exhaustive "
        "chaque aspect attendu selon les règles du livrable, même les sections "
        "qui pourraient sembler évidentes."
    ),
    "wrong_tone": (
        "Le ton précédent était inadapté. Adopte un ton professionnel factuel, "
        "sans tournures marketing, sans sur-emphase, conforme à un document "
        "technique d'ingénierie suisse."
    ),
    "factual_error": (
        "Une erreur factuelle a été détectée (valeur, calcul, référence). "
        "Revalide toutes les affirmations chiffrées avec les données d'input, "
        "et marque explicitement toute valeur incertaine avec 'Hypothèse :' "
        "au lieu de l'affirmer."
    ),
    "wrong_structure": (
        "La structure / le plan du document est à revoir. Respecte strictement "
        "le plan attendu pour ce type de livrable et justifie chaque section."
    ),
    "too_long": (
        "Le rendu précédent était trop long. Concentre-toi sur l'essentiel, "
        "supprime les paragraphes redondants, privilégie les tableaux aux "
        "longues énumérations."
    ),
    "too_short": (
        "Le rendu précédent manquait de profondeur. Développe davantage "
        "les justifications techniques et les références normatives."
    ),
    "language_issue": (
        "La qualité de langue doit être améliorée : français technique suisse "
        "romand, phrases courtes et précises, pas d'anglicismes, pas de "
        "constructions maladroites."
    ),
    "assumption_wrong": (
        "Une hypothèse posée dans la version précédente n'était pas valable "
        "pour ce projet. Liste désormais TOUTES les hypothèses en début de "
        "document, et distingue clairement les données vérifiées (source) "
        "des hypothèses de travail."
    ),
    "citation_missing": (
        "Les références et sources étaient insuffisantes. Pour chaque "
        "affirmation normative, cite la référence complète "
        "(norme, article, canton). Les valeurs numériques doivent être sourcées."
    ),
    "other": "",  # géré par le custom_feedback seul
}


def build_regeneration_instructions(
    regen_context: Optional[dict[str, Any]],
) -> str:
    """Construit le bloc d'instructions à ajouter au prompt utilisateur.

    Retourne `""` si pas de contexte de régénération (1ère génération).
    Sinon retourne un bloc markdown clairement délimité.

    Usage dans un agent :
        from app.agent.prompts.regeneration import build_regeneration_instructions

        regen_block = build_regeneration_instructions(
            params.get("regeneration_context")
        )
        user_content = base_user_content + regen_block
    """
    if not regen_context:
        return ""

    reasons = regen_context.get("reasons") or []
    custom = (regen_context.get("custom_feedback") or "").strip()
    sections = regen_context.get("target_sections") or []
    attempt = regen_context.get("attempt", 1)
    max_attempts = regen_context.get("max_attempts", 5)
    previous_preview = (regen_context.get("previous_output_preview") or "").strip()

    lines: list[str] = [
        "",
        "---",
        "",
        f"## ⚠ RÉGÉNÉRATION CIBLÉE (tentative {attempt}/{max_attempts})",
        "",
        "**L'utilisateur a demandé une régénération** de ta version précédente "
        "pour les raisons suivantes. Tu dois PRODUIRE UNE NOUVELLE VERSION "
        "qui corrige spécifiquement ces points tout en conservant ce qui était "
        "bon dans la version précédente (règle anti-régression).",
        "",
    ]

    # Motifs structurés
    if reasons:
        lines.append("### Motifs signalés")
        lines.append("")
        for r in reasons:
            instruction = REASON_INSTRUCTIONS.get(r, "")
            if instruction:
                lines.append(f"- **{r}** — {instruction}")
            else:
                lines.append(f"- **{r}**")
        lines.append("")

    # Feedback libre
    if custom:
        lines.append("### Commentaire de l'utilisateur")
        lines.append("")
        # Citation markdown du feedback
        for line in custom.split("\n"):
            lines.append(f"> {line}")
        lines.append("")

    # Sections ciblées
    if sections:
        lines.append("### Sections à retravailler en priorité")
        lines.append("")
        for s in sections:
            lines.append(f"- {s}")
        lines.append("")
        lines.append(
            "Pour les sections NON listées ci-dessus, conserve exactement "
            "le contenu et la forme de la version précédente (ne réécris que "
            "ce qui est nécessaire)."
        )
        lines.append("")

    # Extrait précédent
    if previous_preview:
        lines.append("### Extrait de la version précédente (pour référence)")
        lines.append("")
        lines.append("```")
        lines.append(previous_preview[:1500])
        if len(previous_preview) >= 1500:
            lines.append("…")
        lines.append("```")
        lines.append("")

    lines.append("### Règles de régénération")
    lines.append("")
    lines.append(
        "1. Ne régresse pas : ce qui était correct dans la version précédente "
        "doit rester correct."
    )
    lines.append(
        "2. Adresse chaque motif signalé explicitement — l'utilisateur doit "
        "sentir que tu as entendu son feedback."
    )
    lines.append(
        "3. Ne multiplie pas les disclaimers ou excuses — produis directement "
        "la version corrigée."
    )
    lines.append(
        "4. Si un motif est contradictoire avec les règles métier ou normatives, "
        "signale-le en début de document (section « Note à l'utilisateur ») "
        "au lieu de forcer une version incorrecte."
    )
    lines.append("")

    return "\n".join(lines)


def get_model_override_for_regeneration(
    regen_context: Optional[dict[str, Any]],
    current_model: str,
) -> Optional[str]:
    """Si l'utilisateur a coché `upgrade_model`, retourne le modèle supérieur.

    Haiku → Sonnet → Opus.
    Si déjà sur Opus ou pas d'upgrade demandé, retourne None.
    """
    if not regen_context or not regen_context.get("upgrade_model"):
        return None

    if "haiku" in current_model:
        return "claude-sonnet-4-6"
    if "sonnet" in current_model:
        return "claude-opus-4-6"
    return None  # déjà Opus
