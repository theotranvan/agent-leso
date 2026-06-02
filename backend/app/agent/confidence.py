"""Calcul d'un score de confiance sur les documents produits par l'agent.

Objectif (Levier 1 du plan de réduction du goulot de validation)
================================================================
Avant qu'un document soit présenté à l'ingénieur responsable, l'agent
s'auto-évalue sur des critères objectifs et déterministes. Le score (0–100)
permet de router le document :

  - score ≥ HIGH_CONFIDENCE (85) → "prêt à approuver" (relecture rapide)
  - MEDIUM ≤ score < HIGH        → "à relire" (lecture attentive ciblée)
  - score < MEDIUM (60)          → "révision nécessaire" (l'agent signale lui-même)

Le score N'EST PAS une garantie de conformité — c'est un indicateur de risque
qui aide l'ingénieur à prioriser son attention. La responsabilité professionnelle
reste entièrement humaine.

Philosophie du calcul
======================
Le score combine des checks déterministes (présence de sections, cohérence des
chiffres, citations de normes, marqueurs d'incertitude) PLUS, optionnellement,
les warnings remontés par les connecteurs métier (Lesosai, Scia) et l'ingestion.

On ne fait AUCUN appel LLM ici : le scoring doit être rapide, gratuit en tokens,
et reproductible. C'est un filet de sécurité mécanique, pas une seconde opinion IA.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ==========================================================================
# SEUILS
# ==========================================================================

HIGH_CONFIDENCE_THRESHOLD = 85   # ≥ → prêt à approuver
MEDIUM_CONFIDENCE_THRESHOLD = 60  # ≥ → à relire ; < → révision nécessaire


class ConfidenceLevel(str, Enum):
    HIGH = "high"        # prêt à approuver
    MEDIUM = "medium"    # à relire
    LOW = "low"          # révision nécessaire


# Marqueurs d'incertitude que l'agent peut laisser dans un document
UNCERTAINTY_MARKERS = (
    "[À COMPLÉTER",
    "[A COMPLETER",
    "[À VÉRIFIER",
    "[A VERIFIER",
    "[INCERTAIN",
    "[HYPOTHÈSE",
    "[HYPOTHESE",
    "à confirmer",
    "à valider",
    "sous réserve",
    "non disponible",
    "donnée manquante",
)

# Normes suisses attendues selon le type de tâche (pour vérifier les citations)
EXPECTED_NORMS_BY_TASK = {
    "justificatif_sia_380_1": ["SIA 380/1", "SIA 380/4"],
    "calcul_cecb": ["CECB", "SIA 380/1"],
    "note_calcul_sia_260_267": ["SIA 260", "SIA 261", "SIA 262"],
    "redaction_cctp": ["SIA 451"],
    "descriptif_can_sia_451": ["SIA 451"],
    "aeai_rapport": ["AEAI"],
    "aeai_checklist_generation": ["AEAI"],
    "idc_geneve_rapport": ["IDC", "SIA 2031"],
    "dossier_mise_enquete": ["LATC", "AEAI"],
    "chiffrage_dpgf": ["CFC"],
    "verification_eurocode": ["EN 1992", "Eurocode"],
}


# ==========================================================================
# RÉSULTAT
# ==========================================================================

@dataclass
class ConfidenceCheck:
    """Un critère de vérification individuel."""

    name: str
    passed: bool
    weight: int               # poids du critère dans le score
    detail: str = ""
    is_alert: bool = False    # True → ce point doit être signalé à l'ingénieur


@dataclass
class ConfidenceScore:
    """Résultat complet du scoring."""

    score: int                              # 0–100
    level: ConfidenceLevel
    checks: list[ConfidenceCheck] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)  # points à vérifier (Levier 2)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level.value,
            "ready_to_approve": self.level == ConfidenceLevel.HIGH,
            "alerts": self.alerts,
            "summary": self.summary,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "weight": c.weight,
                    "detail": c.detail,
                    "is_alert": c.is_alert,
                }
                for c in self.checks
            ],
        }


# ==========================================================================
# CALCUL
# ==========================================================================

def compute_confidence(
    task_type: str,
    document_html: str,
    *,
    connector_warnings: list[str] | None = None,
    ingestion_warnings: list[str] | None = None,
    expected_sections: list[str] | None = None,
    numeric_checks: dict[str, bool] | None = None,
) -> ConfidenceScore:
    """Calcule le score de confiance d'un document.

    Args:
        task_type: type de tâche (pour vérifier les normes attendues)
        document_html: le contenu HTML produit par l'agent
        connector_warnings: warnings remontés par Lesosai/Scia (déjà calculés)
        ingestion_warnings: warnings de l'ingestion documentaire
        expected_sections: titres de sections qui doivent être présentes
        numeric_checks: dict {nom: bool} de vérifications de cohérence chiffrée
                        déjà effectuées par le module métier
    """
    checks: list[ConfidenceCheck] = []
    alerts: list[str] = []
    text = document_html or ""
    text_lower = text.lower()

    # ---- Check 1 : document non vide et de taille raisonnable ----
    length = len(text.strip())
    if length < 200:
        checks.append(ConfidenceCheck(
            "Contenu suffisant", False, 25,
            f"Document très court ({length} car.) — production probablement incomplète",
            is_alert=True,
        ))
        alerts.append("Le document est anormalement court — vérifier qu'il est complet.")
    else:
        checks.append(ConfidenceCheck(
            "Contenu suffisant", True, 25,
            f"{length} caractères produits",
        ))

    # ---- Check 2 : marqueurs d'incertitude laissés par l'agent ----
    found_markers = [m for m in UNCERTAINTY_MARKERS if m.lower() in text_lower]
    if found_markers:
        # Compter les occurrences pour pondérer
        n_occurrences = sum(text_lower.count(m.lower()) for m in found_markers)
        checks.append(ConfidenceCheck(
            "Pas de données manquantes", False, 20,
            f"{n_occurrences} marqueur(s) d'incertitude : {', '.join(set(found_markers))}",
            is_alert=True,
        ))
        alerts.append(
            f"L'agent a laissé {n_occurrences} zone(s) à compléter ou vérifier "
            f"(rechercher : {', '.join(sorted(set(found_markers)))[:80]})."
        )
    else:
        checks.append(ConfidenceCheck(
            "Pas de données manquantes", True, 20,
            "Aucun marqueur d'incertitude détecté",
        ))

    # ---- Check 3 : normes attendues citées ----
    expected_norms = EXPECTED_NORMS_BY_TASK.get(task_type, [])
    if expected_norms:
        missing = [n for n in expected_norms if n.lower() not in text_lower]
        if missing:
            checks.append(ConfidenceCheck(
                "Normes de référence citées", False, 15,
                f"Normes attendues absentes : {', '.join(missing)}",
                is_alert=True,
            ))
            alerts.append(
                f"Norme(s) attendue(s) non citée(s) : {', '.join(missing)} — "
                f"vérifier que le référentiel est complet."
            )
        else:
            checks.append(ConfidenceCheck(
                "Normes de référence citées", True, 15,
                f"Toutes les normes attendues présentes ({', '.join(expected_norms)})",
            ))
    else:
        # Pas de normes attendues pour ce type → check neutre validé
        checks.append(ConfidenceCheck(
            "Normes de référence citées", True, 15,
            "Aucune norme spécifique requise pour ce type de tâche",
        ))

    # ---- Check 4 : sections attendues présentes ----
    if expected_sections:
        missing_sections = [s for s in expected_sections if s.lower() not in text_lower]
        if missing_sections:
            checks.append(ConfidenceCheck(
                "Sections complètes", False, 15,
                f"Sections manquantes : {', '.join(missing_sections)}",
                is_alert=True,
            ))
            alerts.append(
                f"Section(s) attendue(s) manquante(s) : {', '.join(missing_sections)}."
            )
        else:
            checks.append(ConfidenceCheck(
                "Sections complètes", True, 15,
                "Toutes les sections attendues présentes",
            ))
    else:
        checks.append(ConfidenceCheck(
            "Sections complètes", True, 15,
            "Pas de structure de sections imposée",
        ))

    # ---- Check 5 : cohérence chiffrée (fournie par le module métier) ----
    if numeric_checks:
        failed_numeric = [k for k, ok in numeric_checks.items() if not ok]
        if failed_numeric:
            checks.append(ConfidenceCheck(
                "Cohérence des calculs", False, 15,
                f"Vérifications échouées : {', '.join(failed_numeric)}",
                is_alert=True,
            ))
            for k in failed_numeric:
                alerts.append(f"Incohérence de calcul détectée : {k}.")
        else:
            checks.append(ConfidenceCheck(
                "Cohérence des calculs", True, 15,
                f"{len(numeric_checks)} vérification(s) chiffrée(s) OK",
            ))
    else:
        checks.append(ConfidenceCheck(
            "Cohérence des calculs", True, 15,
            "Pas de vérification chiffrée applicable",
        ))

    # ---- Check 6 : warnings connecteurs (Lesosai, Scia) ----
    cw = connector_warnings or []
    # On ignore les warnings purement informatifs (stub, watched-folder)
    serious_cw = [
        w for w in cw
        if not any(kw in w.lower() for kw in ("stub", "watched-folder", "input_dir", "output_dir", "créé"))
    ]
    if serious_cw:
        for w in serious_cw[:3]:
            alerts.append(f"Connecteur : {w[:120]}")

    # ---- Check 7 : warnings ingestion ----
    iw = ingestion_warnings or []
    if iw:
        for w in iw[:2]:
            alerts.append(f"Ingestion : {w[:120]}")

    # ==================== SCORE FINAL ====================
    total_weight = sum(c.weight for c in checks)
    earned = sum(c.weight for c in checks if c.passed)
    score = round(earned / total_weight * 100) if total_weight else 0

    # Pénalité supplémentaire si beaucoup d'alertes connecteurs/ingestion
    extra_alerts = len(serious_cw) + len(iw)
    if extra_alerts >= 3:
        score = max(0, score - 10)

    # Niveau
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        level = ConfidenceLevel.HIGH
    elif score >= MEDIUM_CONFIDENCE_THRESHOLD:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    # Résumé lisible pour l'ingénieur
    if level == ConfidenceLevel.HIGH:
        summary = (
            f"Confiance élevée ({score}%). Document prêt pour approbation, "
            f"relecture rapide recommandée."
        )
    elif level == ConfidenceLevel.MEDIUM:
        summary = (
            f"Confiance moyenne ({score}%). {len(alerts)} point(s) à vérifier "
            f"avant approbation."
        )
    else:
        summary = (
            f"Confiance faible ({score}%). Révision nécessaire — "
            f"{len(alerts)} point(s) signalé(s)."
        )

    return ConfidenceScore(
        score=score,
        level=level,
        checks=checks,
        alerts=alerts,
        summary=summary,
    )
