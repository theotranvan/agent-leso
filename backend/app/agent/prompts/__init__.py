"""Helpers de construction de prompts partagés entre agents."""
# Ré-export des constantes et fonctions legacy (ancien prompts.py)
from app.agent.prompts._legacy import (  # noqa: F401
    get_system_prompt,
    get_normes_for_lot,
)

# Nouveau (V5) : instructions de régénération structurées
from app.agent.prompts.regeneration import (  # noqa: F401
    build_regeneration_instructions,
    get_model_override_for_regeneration,
)

# Expose toutes les autres constantes PROMPTS_* du legacy
try:
    from app.agent.prompts._legacy import PROMPTS  # noqa: F401
except ImportError:
    pass

__all__ = [
    "get_system_prompt",
    "get_normes_for_lot",
    "build_regeneration_instructions",
    "get_model_override_for_regeneration",
]
