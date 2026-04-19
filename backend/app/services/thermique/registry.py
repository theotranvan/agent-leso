"""Registry des moteurs thermiques disponibles."""
from app.services.thermique.engine_interface import ThermalEngine
from app.services.thermique.lesosai_file import LesosaiFileEngine
from app.services.thermique.lesosai_stub import LesosaiStubEngine


_ENGINES: dict[str, ThermalEngine] = {
    "lesosai_stub": LesosaiStubEngine(),
    "lesosai_file": LesosaiFileEngine(),
}


def get_engine(name: str) -> ThermalEngine:
    """Retourne un moteur thermique par nom.

    Disponibles en V2 :
      - 'lesosai_stub' : dummy, pour dev et estimations avant-projet uniquement
      - 'lesosai_file' : génère fichier + fiche saisie opérateur (scénario B)

    À brancher en V3 : 'lesosai_api' (après qualification E4tech), 'internal' (moteur alternatif).
    """
    engine = _ENGINES.get(name)
    if not engine:
        raise ValueError(f"Moteur thermique inconnu : {name}. Disponibles : {list(_ENGINES.keys())}")
    return engine


def list_engines() -> list[dict]:
    return [
        {
            "name": "lesosai_stub",
            "label": "Calcul indicatif rapide (stub)",
            "description": "Estimation approximative sans équivalence SIA 380/1 officielle. Avant-projet uniquement.",
            "use_for": ["avant_projet", "test"],
        },
        {
            "name": "lesosai_file",
            "label": "Export vers Lesosai (fichier + fiche saisie)",
            "description": "Génère un dossier qui accélère massivement la saisie dans Lesosai. Calcul officiel fait dans Lesosai.",
            "use_for": ["production", "justificatif_officiel"],
        },
    ]
