"""Extraction d'une spec pré-BIM depuis des entrées hétérogènes.

Sources :
- Texte libre (programme architecte)
- Tableau de surfaces (texte ou Excel/CSV)
- Plans PDF (dimensions via OCR si présent)
- Inputs utilisateur via formulaire

Retourne une spec compatible PreBIMGenerator.
"""
import json
import logging
import re
from typing import Any

from app.agent.router import call_llm

logger = logging.getLogger(__name__)


EXTRACTION_SYSTEM = """Tu es un assistant technique BET qui extrait des données de programme architectural pour construire un pré-modèle BIM simplifié.

À partir du texte fourni, produis un JSON strict au format :

{
  "project_name": "...",
  "building_name": "...",
  "site_name": "...",
  "canton": "GE|VD|NE|FR|VS|JU",
  "operation_type": "neuf|renovation|transformation",
  "affectation": "logement_collectif|logement_individuel|administration|commerce|erp|industriel",
  "nb_logements": 0,
  "storeys": [
    {"name": "Rez", "elevation_m": 0, "height_m": 3.0, "area_m2": 250, "usage": "logement_collectif"}
  ],
  "envelope": {
    "plan_width_m": 25, "plan_depth_m": 10,
    "wall_composition_key": "mur_ext_neuf_standard",
    "roof_composition_key": "toit_neuf_perform",
    "slab_ground_composition_key": "dalle_sur_terrain_neuf",
    "window_ratio_by_orientation": {"N": 0.15, "S": 0.35, "E": 0.25, "W": 0.25},
    "window_u_value": 1.0,
    "window_g_value": 0.55
  },
  "assumptions": ["liste des hypothèses faites faute de données"],
  "missing_info": ["liste des informations manquantes critiques"]
}

RÈGLES :
- Si une info manque, utilise une valeur par défaut raisonnable ET liste-la dans "assumptions"
- plan_width_m et plan_depth_m : estime à partir des surfaces d'étage (rectangle équivalent)
- Ne fabrique pas de données : si la hauteur d'étage n'est pas donnée, utilise 2.8m (logement) ou 3.0m (tertiaire) par défaut
- Ne sors QUE le JSON, sans commentaire autour"""


COMPOSITION_KEYS_VALID = [
    "mur_ext_neuf_perform", "mur_ext_neuf_standard", "mur_ext_renovation",
    "toit_neuf_perform",
    "dalle_sur_terrain_neuf", "plancher_inter_etage",
]


async def extract_spec_from_text(text: str, hints: dict | None = None) -> dict:
    """Extrait une spec pré-BIM depuis un programme textuel via LLM.

    hints : dict optionnel {canton, operation_type, affectation, plan_width_m, etc.}
    Les hints overrident ce que le LLM aurait déduit.
    """
    if not text or not text.strip():
        raise ValueError("Texte vide")

    hints = hints or {}

    user_content = f"""Extraire la spec pré-BIM du programme suivant.

HINTS UTILISATEUR (à respecter en priorité si renseignés) :
{json.dumps(hints, ensure_ascii=False, indent=2)}

PROGRAMME :
{text[:20000]}

Retourne uniquement le JSON."""

    result = await call_llm(
        task_type="extraction_metadata",
        system_prompt=EXTRACTION_SYSTEM,
        user_content=user_content,
        max_tokens=3000,
        temperature=0.1,
    )

    raw = result["text"].strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1]) if raw.endswith("```") else "\n".join(raw.split("\n")[1:])
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Impossible de parser la spec depuis le LLM : {raw[:200]}")

    spec = json.loads(raw[start:end + 1])

    # Validation & fallbacks
    spec = _validate_and_fill_defaults(spec, hints)
    return spec


def _validate_and_fill_defaults(spec: dict, hints: dict) -> dict:
    """Valide la spec et complète par des défauts si incomplète."""
    out = {**spec}

    # Overrides hints
    for k in ["canton", "operation_type", "affectation", "project_name"]:
        if hints.get(k):
            out[k] = hints[k]

    # Défauts étages
    if not out.get("storeys"):
        out["storeys"] = [
            {"name": "Rez", "elevation_m": 0, "height_m": 3.0, "area_m2": 200,
             "usage": out.get("affectation", "logement_collectif")},
        ]

    # Recalcule elevation si absent
    current_elev = 0.0
    for st in out["storeys"]:
        if "elevation_m" not in st or st["elevation_m"] is None:
            st["elevation_m"] = current_elev
        if "height_m" not in st or not st["height_m"]:
            st["height_m"] = 3.0 if out.get("affectation", "").startswith("admin") else 2.8
        current_elev = st["elevation_m"] + st["height_m"]

    # Enveloppe
    env = out.get("envelope") or {}
    env.setdefault("plan_width_m", 20.0)
    env.setdefault("plan_depth_m", 10.0)

    operation = out.get("operation_type", "neuf")
    if operation == "renovation":
        env.setdefault("wall_composition_key", "mur_ext_renovation")
    else:
        env.setdefault("wall_composition_key", "mur_ext_neuf_standard")
    env.setdefault("roof_composition_key", "toit_neuf_perform")
    env.setdefault("slab_ground_composition_key", "dalle_sur_terrain_neuf")
    env.setdefault("window_ratio_by_orientation", {"N": 0.15, "S": 0.30, "E": 0.25, "W": 0.25})
    env.setdefault("window_u_value", 1.0)
    env.setdefault("window_g_value", 0.55)

    # Clés de composition valides
    for key_field in ["wall_composition_key", "roof_composition_key", "slab_ground_composition_key"]:
        if env.get(key_field) not in COMPOSITION_KEYS_VALID:
            env[key_field] = {
                "wall_composition_key": "mur_ext_neuf_standard",
                "roof_composition_key": "toit_neuf_perform",
                "slab_ground_composition_key": "dalle_sur_terrain_neuf",
            }[key_field]

    out["envelope"] = env

    # Assumptions / missing
    out.setdefault("assumptions", [])
    out.setdefault("missing_info", [])

    return out


def extract_surfaces_from_table_text(text: str) -> list[dict]:
    """Extrait un tableau de surfaces par étage depuis du texte libre.

    Patterns recherchés : "R+1 | 250 m²" / "Étage 2 : 180m2" / etc.
    """
    results = []
    # Pattern simple
    patterns = [
        r"(rez|r\+\d+|\w+[éè]tage \d+|sous-sol|comble|attique)[\s:|/]+(\d+[\.,]?\d*)\s*m[²2]",
        r"niveau\s*(\d+)[\s:|/]+(\d+[\.,]?\d*)\s*m[²2]",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            level_label = m.group(1).strip()
            try:
                area = float(m.group(2).replace(",", "."))
                results.append({"label": level_label, "area_m2": area})
            except ValueError:
                pass

    # Déduplication
    seen = set()
    unique = []
    for r in results:
        key = r["label"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique
