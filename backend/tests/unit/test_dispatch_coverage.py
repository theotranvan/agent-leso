"""Cohérence routage ↔ dispatch ↔ tarification.

Un type de tâche présent dans ROUTING_TABLE mais absent du dispatch de
l'orchestrateur → l'ingénieur reçoit "Type de tâche non supporté" : échec
silencieux côté produit. Inversement, un dispatch sans entrée de routage
tombe sur le modèle par défaut sans justification.

On parse le source de l'orchestrateur (sans l'exécuter : pas de DB/LLM) pour
extraire les task_types réellement dispatchés, et on les croise avec la table
de routage et la table de tarification.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.agent.router import (
    MODEL_PRICING_USD,
    ROUTING_TABLE,
    estimate_cost_chf,
    estimate_cost_eur,
    get_model_for_task,
)

ORCHESTRATOR = Path(__file__).resolve().parent.parent.parent / "app" / "agent" / "orchestrator.py"


def _dispatched_task_types() -> set[str]:
    """Extrait tous les task_type comparés dans l'orchestrateur.

    Couvre `task_type == "x"` et `task_type in ("a", "b", ...)`.
    """
    src = ORCHESTRATOR.read_text()
    found: set[str] = set()
    # task_type == "xxx"
    for m in re.finditer(r'task_type\s*==\s*"([a-z0-9_]+)"', src):
        found.add(m.group(1))
    # task_type in ("a", "b", ...)
    for block in re.finditer(r'task_type\s+in\s*\(([^)]*)\)', src):
        for s in re.finditer(r'"([a-z0-9_]+)"', block.group(1)):
            found.add(s.group(1))
    return found


DISPATCHED = _dispatched_task_types()


class TestDispatchCoverage:
    def test_orchestrator_dispatches_something(self):
        # garde-fou : le parsing a bien trouvé des types
        assert len(DISPATCHED) >= 20, f"Parsing douteux : {sorted(DISPATCHED)}"

    def test_every_routed_task_is_dispatched(self):
        """Tout type routé vers un modèle DOIT avoir un handler (sinon erreur user)."""
        # Types connus comme déterministes/alias gérés hors routing strict.
        orphans = sorted(t for t in ROUTING_TABLE if t not in DISPATCHED)
        assert not orphans, (
            "Types routés sans dispatch dans l'orchestrateur "
            f"(→ 'Type de tâche non supporté' pour l'ingénieur) : {orphans}"
        )

    def test_every_dispatched_task_has_a_model(self):
        """Tout type dispatché a un modèle explicite (pas le défaut implicite)."""
        # 'rapport_chantier' est dispatché et tolère le défaut Sonnet.
        tolerated_default = {"rapport_chantier"}
        missing = sorted(
            t for t in DISPATCHED
            if t not in ROUTING_TABLE and t not in tolerated_default
        )
        assert not missing, f"Types dispatchés sans entrée de routage : {missing}"

    def test_routing_returns_known_models(self):
        valid = set(MODEL_PRICING_USD.keys())
        for task_type in ROUTING_TABLE:
            model = get_model_for_task(task_type)
            assert model in valid, f"{task_type} → modèle inconnu {model}"

    def test_default_model_is_priced(self):
        # un type inconnu retombe sur le défaut, qui doit être tarifé.
        default_model = get_model_for_task("type_totalement_inconnu")
        assert default_model in MODEL_PRICING_USD


class TestCostEstimation:
    def test_cost_is_positive_and_ordered_by_model(self):
        # Opus > Sonnet > Haiku pour un même volume.
        models = sorted(MODEL_PRICING_USD.keys(),
                        key=lambda m: MODEL_PRICING_USD[m]["output"])
        costs = [estimate_cost_chf(m, 1_000_000, 1_000_000) for m in models]
        assert costs == sorted(costs), f"Coûts non monotones : {list(zip(models, costs))}"
        assert all(c > 0 for c in costs)

    def test_zero_tokens_zero_cost(self):
        for m in MODEL_PRICING_USD:
            assert estimate_cost_chf(m, 0, 0) == 0.0
            assert estimate_cost_eur(m, 0, 0) == 0.0

    def test_chf_and_eur_consistent_sign(self):
        for m in MODEL_PRICING_USD:
            assert estimate_cost_chf(m, 1000, 1000) > 0
            assert estimate_cost_eur(m, 1000, 1000) > 0

    def test_output_more_expensive_than_input(self):
        # sur tous les modèles Anthropic, l'output coûte plus que l'input.
        for m, pricing in MODEL_PRICING_USD.items():
            assert pricing["output"] > pricing["input"], f"{m} : output ≤ input"
