"""Parcours d'affaire BET — phases SIA 102 et actions guidées.

Objectif
========
Guider l'ingénieur à travers le cycle de vie d'un projet comme il le ferait
naturellement, en proposant à chaque phase les actions pertinentes. Le parcours
est INDICATIF, pas contraignant : l'ingénieur peut sauter des phases, en faire
plusieurs en parallèle, ou réorganiser selon les spécificités de son affaire.

Philosophie
===========
- Chaque phase a des actions "recommandées" et des prérequis "suggérés".
- Rien n'est verrouillé de force : un prérequis non satisfait affiche un conseil,
  pas un blocage. L'ingénieur garde la main.
- L'objectif est de réduire la charge cognitive : ne montrer que ce qui est
  pertinent à l'instant T, dans l'ordre logique du métier.
- Modulable : une organisation peut désactiver des phases (ex: bureau qui ne
  fait pas de suivi de chantier) via les réglages.

Référence : phases SIA 102 (prestations des architectes et ingénieurs).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PhaseAction:
    """Une action recommandée dans une phase."""

    task_type: str
    label: str
    description: str
    optional: bool = False           # action facultative dans cette phase
    requires: list[str] = field(default_factory=list)  # task_types suggérés en amont


@dataclass
class ProjectPhase:
    """Une phase du parcours d'affaire."""

    key: str
    sia_code: str
    label: str
    description: str
    order: int
    actions: list[PhaseAction] = field(default_factory=list)
    optional: bool = False           # phase que certaines orgs peuvent ignorer

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "sia_code": self.sia_code,
            "label": self.label,
            "description": self.description,
            "order": self.order,
            "optional": self.optional,
            "actions": [
                {
                    "task_type": a.task_type,
                    "label": a.label,
                    "description": a.description,
                    "optional": a.optional,
                    "requires": a.requires,
                }
                for a in self.actions
            ],
        }


# ==========================================================================
# DÉFINITION DU PARCOURS STANDARD (Suisse romande, CVSE)
# ==========================================================================

PROJECT_JOURNEY: list[ProjectPhase] = [
    ProjectPhase(
        key="initiation",
        sia_code="—",
        label="Création de l'affaire",
        description="Saisie des données de base du projet : localisation, gabarit, "
                    "labels visés, phase de départ.",
        order=1,
        actions=[
            PhaseAction(
                task_type="project_setup",
                label="Renseigner les données projet",
                description="Adresse, commune, SRE, nombre de logements, affectation, "
                            "labels (Minergie-P, CVSE), phase SIA de démarrage.",
            ),
        ],
    ),
    ProjectPhase(
        key="avant_projet",
        sia_code="31",
        label="Avant-projet",
        description="Vérifier la faisabilité réglementaire et choisir les grands "
                    "principes techniques (système de chauffage, ventilation).",
        order=2,
        actions=[
            PhaseAction(
                "controle_reglementaire_vaud",
                "Vérification urbanistique",
                "Conformité au règlement communal (IUS, COS, hauteurs, gabarits).",
            ),
            PhaseAction(
                "simulation_energetique_rapide",
                "Simulation énergétique rapide",
                "Première estimation du besoin de chaleur et choix de système.",
            ),
        ],
    ),
    ProjectPhase(
        key="projet_ouvrage",
        sia_code="32",
        label="Projet de l'ouvrage",
        description="Dimensionnements et justificatifs techniques détaillés. "
                    "C'est ici qu'on passe par Lesosai et Scia.",
        order=3,
        actions=[
            PhaseAction(
                "justificatif_sia_380_1",
                "Justificatif thermique SIA 380/1",
                "Export gbXML vers Lesosai, calcul du besoin de chaleur, "
                "vérification des exigences Minergie-P.",
                requires=["simulation_energetique_rapide"],
            ),
            PhaseAction(
                "note_calcul_sia_260_267",
                "Note de calcul structure",
                "Dimensionnement des éléments porteurs (Scia / vérification analytique).",
            ),
            PhaseAction(
                "calcul_cecb",
                "Calcul CECB",
                "Certificat énergétique cantonal des bâtiments.",
                optional=True,
            ),
        ],
    ),
    ProjectPhase(
        key="autorisation",
        sia_code="33",
        label="Mise à l'enquête / autorisation",
        description="Constitution du dossier réglementaire à déposer auprès de la "
                    "commune et des autorités cantonales.",
        order=4,
        actions=[
            PhaseAction(
                "dossier_mise_enquete",
                "Dossier de mise à l'enquête",
                "Pièces réglementaires pour le permis de construire.",
                requires=["justificatif_sia_380_1"],
            ),
            PhaseAction(
                "aeai_checklist_generation",
                "Checklist AEAI (incendie)",
                "Points de contrôle prévention incendie selon directives AEAI.",
            ),
            PhaseAction(
                "idc_geneve_rapport",
                "IDC — Indice de dépense de chaleur",
                "Calcul et formulaire OCEN (obligatoire logement locatif).",
                optional=True,
            ),
        ],
    ),
    ProjectPhase(
        key="appel_offres",
        sia_code="41",
        label="Appel d'offres",
        description="Production des documents de consultation des entreprises : "
                    "descriptifs techniques et bordereaux de prix.",
        order=5,
        actions=[
            PhaseAction(
                "redaction_cctp",
                "CCTP / descriptif CAN (tous lots)",
                "Cahier des clauses techniques par lot CFC.",
                requires=["justificatif_sia_380_1", "note_calcul_sia_260_267"],
            ),
            PhaseAction(
                "chiffrage_dpgf",
                "DPGF / soumission",
                "Décomposition du prix global et forfaitaire par lot.",
                requires=["redaction_cctp"],
            ),
            PhaseAction(
                "coordination_inter_lots",
                "Coordination inter-lots",
                "Interfaces techniques entre lots et planning de réservations.",
            ),
        ],
    ),
    ProjectPhase(
        key="execution",
        sia_code="51-52",
        label="Exécution / chantier",
        description="Suivi de la réalisation : observations de chantier, réponses "
                    "aux autorités, métrés.",
        order=6,
        optional=True,
        actions=[
            PhaseAction(
                "reponse_observations_autorite",
                "Réponses aux observations des autorités",
                "Traitement des remarques de la commune ou du canton.",
            ),
            PhaseAction(
                "rapport_chantier",
                "Rapport de visite de chantier",
                "Compte-rendu structuré à partir de photos et notes de terrain.",
            ),
            PhaseAction(
                "metres_automatiques_ifc",
                "Métrés automatiques IFC",
                "Quantitatifs extraits de la maquette BIM.",
                optional=True,
            ),
        ],
    ),
    ProjectPhase(
        key="cloture",
        sia_code="53",
        label="Mise en service / clôture",
        description="Réception, dossier des ouvrages exécutés et formalités finales.",
        order=7,
        optional=True,
        actions=[
            PhaseAction(
                "doe_compilation",
                "Dossier des ouvrages exécutés (DOE)",
                "Compilation des documents de fin de chantier.",
            ),
            PhaseAction(
                "idc_geneve_rapport",
                "Formulaire IDC final (OCEN)",
                "Indice de dépense de chaleur après mise en service.",
                optional=True,
            ),
        ],
    ),
]


# Index pour accès rapide
PHASE_BY_KEY = {p.key: p for p in PROJECT_JOURNEY}
PHASE_ORDER = [p.key for p in sorted(PROJECT_JOURNEY, key=lambda x: x.order)]


# ==========================================================================
# CALCUL DE L'ÉTAT D'AVANCEMENT
# ==========================================================================

def compute_journey_state(
    completed_task_types: list[str],
    approved_task_types: list[str] | None = None,
    current_phase: str | None = None,
    disabled_phases: list[str] | None = None,
) -> dict[str, Any]:
    """Calcule l'état d'avancement d'une affaire dans le parcours.

    Args:
        completed_task_types: types de tâches déjà terminées (au moins une fois)
        approved_task_types: types de tâches approuvées (validation ingénieur)
        current_phase: phase courante déclarée du projet
        disabled_phases: phases désactivées par l'organisation (modularité)

    Returns un état complet par phase avec progression et action recommandée.
    """
    completed = set(completed_task_types or [])
    approved = set(approved_task_types or [])
    disabled = set(disabled_phases or [])

    phases_state = []
    next_recommended = None

    for phase in sorted(PROJECT_JOURNEY, key=lambda x: x.order):
        if phase.key in disabled:
            continue

        actions_state = []
        required_actions = [a for a in phase.actions if not a.optional]
        done_required = 0

        for action in phase.actions:
            is_done = action.task_type in completed
            is_approved = action.task_type in approved
            # Prérequis non satisfaits → on conseille, on ne bloque pas
            missing_reqs = [r for r in action.requires if r not in completed]

            actions_state.append({
                "task_type": action.task_type,
                "label": action.label,
                "description": action.description,
                "optional": action.optional,
                "done": is_done,
                "approved": is_approved,
                "advisory": (
                    f"Recommandé après : {', '.join(missing_reqs)}"
                    if missing_reqs and not is_done else ""
                ),
                "ready": len(missing_reqs) == 0,
            })

            if not action.optional and is_done:
                done_required += 1

            # Première action recommandée non faite et prête
            # (on ignore project_setup et les actions optionnelles pour la reco principale)
            if (
                next_recommended is None
                and not is_done
                and not missing_reqs
                and not action.optional
                and action.task_type != "project_setup"
            ):
                next_recommended = {
                    "phase_key": phase.key,
                    "phase_label": phase.label,
                    "task_type": action.task_type,
                    "label": action.label,
                }

        total_required = len(required_actions)
        progress = round(done_required / total_required * 100) if total_required else 100

        # Statut de la phase
        if progress >= 100:
            status = "completed"
        elif done_required > 0:
            status = "in_progress"
        else:
            status = "not_started"

        phases_state.append({
            **phase.to_dict(),
            "status": status,
            "progress": progress,
            "actions_state": actions_state,
            "is_current": phase.key == current_phase,
        })

    # Progression globale (phases non optionnelles uniquement)
    mandatory_phases = [p for p in phases_state if not p["optional"]]
    if mandatory_phases:
        global_progress = round(
            sum(p["progress"] for p in mandatory_phases) / len(mandatory_phases)
        )
    else:
        global_progress = 0

    return {
        "phases": phases_state,
        "global_progress": global_progress,
        "next_recommended": next_recommended,
        "current_phase": current_phase or (PHASE_ORDER[0] if PHASE_ORDER else None),
    }


def get_journey_definition(disabled_phases: list[str] | None = None) -> dict[str, Any]:
    """Retourne la définition complète du parcours (pour l'UI)."""
    disabled = set(disabled_phases or [])
    return {
        "phases": [
            p.to_dict()
            for p in sorted(PROJECT_JOURNEY, key=lambda x: x.order)
            if p.key not in disabled
        ],
    }
