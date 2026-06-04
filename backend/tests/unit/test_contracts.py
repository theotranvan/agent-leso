"""Tests de non-régression sur les contrats d'entrée qui ont déjà cassé en prod.

Garantissent que :
- la simulation énergétique lit sre_m2 que les params soient à plat OU nichés
  sous "programme" (les deux appelants existent) ;
- la vérification réglementaire du parcours s'adapte au canton du projet.
"""
import pytest

from app.agent.project_journey import compute_journey_state


def _find_control_action(state: dict) -> dict | None:
    for phase in state["phases"]:
        for action in phase["actions_state"]:
            if action["task_type"].startswith("controle_reglementaire_"):
                return action
    return None


def test_journey_control_adapts_to_canton_geneve():
    state = compute_journey_state(completed_task_types=[], canton="GE")
    action = _find_control_action(state)
    assert action is not None
    assert action["task_type"] == "controle_reglementaire_geneve"
    assert "GE" in action["label"]


def test_journey_control_adapts_to_canton_vaud():
    state = compute_journey_state(completed_task_types=[], canton="VD")
    action = _find_control_action(state)
    assert action["task_type"] == "controle_reglementaire_vaud"


def test_journey_control_generic_when_unknown_canton():
    state = compute_journey_state(completed_task_types=[], canton=None)
    action = _find_control_action(state)
    assert action["task_type"] == "controle_reglementaire_canton"


def test_journey_control_done_for_any_variant():
    # Une variante terminée doit marquer l'action faite, quel que soit le canton.
    state = compute_journey_state(
        completed_task_types=["controle_reglementaire_geneve"], canton="VD",
    )
    action = _find_control_action(state)
    assert action["done"] is True


def test_journey_project_setup_done_flag_via_completed():
    state = compute_journey_state(completed_task_types=["project_setup"], canton="GE")
    setup = None
    for phase in state["phases"]:
        for a in phase["actions_state"]:
            if a["task_type"] == "project_setup":
                setup = a
    assert setup is not None and setup["done"] is True


@pytest.mark.asyncio
async def test_simulation_reads_sre_from_nested_programme():
    """Params nichés sous 'programme' : l'agent doit lire sre_m2 (ici 0 → ValueError)."""
    from app.agent.swiss import simulation_rapide_agent

    task = {
        "organization_id": "org-1",
        "input_params": {"programme": {"sre_m2": 0, "canton": "GE"}},
    }
    with pytest.raises(ValueError, match="sre_m2"):
        await simulation_rapide_agent.execute(task)


@pytest.mark.asyncio
async def test_simulation_reads_sre_flat():
    """Params à plat : même lecture de sre_m2 (ici 0 → ValueError)."""
    from app.agent.swiss import simulation_rapide_agent

    task = {
        "organization_id": "org-1",
        "input_params": {"sre_m2": 0, "canton": "GE"},
    }
    with pytest.raises(ValueError, match="sre_m2"):
        await simulation_rapide_agent.execute(task)
