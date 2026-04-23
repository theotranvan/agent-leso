"""Tests du parsing d'observations DALE/DGT - 100% déterministe."""
from __future__ import annotations

import pytest

from app.agent.swiss.observations_agent import (
    THEMATIC_KEYWORDS,
    _classify_theme,
    _parse_observations,
)


COURRIER_DALE_EXEMPLE = """
Département du territoire - Office des autorisations de construire
Service des autorisations de construire
Rue David-Dufour 5, 1205 Genève

Leur référence : DD 112345/1
Notre référence : APA-2024-0789

Objet : Observations relatives à votre demande d'autorisation de construire

Monsieur,

Suite à l'examen de votre dossier du 15.03.2024, nous vous transmettons les observations suivantes :

Observation n°1 - Justificatif énergétique SIA 380/1
Le calcul transmis ne fait pas apparaître la station climatique retenue. Veuillez préciser la station
de référence utilisée selon SIA 2028 et fournir les valeurs climatiques complètes.

Observation n°2 - Indices d'utilisation
L'indice IUS calculé (0.68) dépasse le maximum de la zone de développement 3 (0.55). Une dérogation
au sens de l'article 3 LGZD serait nécessaire. Merci de justifier votre approche.

Observation n°3 - Sécurité incendie AEAI
Le rapport incendie ne précise pas le compartimentage vertical entre les niveaux 3 et 4.
Merci de compléter selon la directive AEAI 15-15f, chapitre 3.

Observation n°4 - Arbres et biodiversité
Un inventaire des arbres protégés sur la parcelle n'a pas été fourni. Veuillez consulter
le SITG et soumettre un plan d'abattage si nécessaire.

Délai de réponse : 30 jours.

Cordialement,
Le Service des autorisations de construire
"""


class TestObservationsParser:
    def test_parse_dale_letter_detects_all_observations(self) -> None:
        obs = _parse_observations(COURRIER_DALE_EXEMPLE)
        assert len(obs) == 4
        assert [o["num"] for o in obs] == [1, 2, 3, 4]

    def test_themes_detected_correctly(self) -> None:
        obs = _parse_observations(COURRIER_DALE_EXEMPLE)
        themes = {o["num"]: o["theme"] for o in obs}
        assert themes[1] == "energie_sia_380_1"
        assert themes[2] == "gabarit_zone"
        assert themes[3] == "incendie_aeai"
        assert themes[4] == "paysage_arbres"

    def test_parse_numbered_list_format(self) -> None:
        text = """Observations de l'autorité :

1. Le plan de situation doit être à l'échelle 1:500
2. L'étude géotechnique est manquante
3. Le concept de mobilité doit être renforcé
"""
        obs = _parse_observations(text)
        assert len(obs) == 3
        assert obs[0]["num"] == 1
        assert "plan de situation" in obs[0]["text"].lower()

    def test_parse_paragraph_format(self) -> None:
        text = """§1 Le projet ne respecte pas l'article 77 LCI concernant les distances aux limites.

§2 Le formulaire énergie I-700 n'est pas signé.

§3 L'acousticien n'a pas produit l'étude SIA 181.
"""
        obs = _parse_observations(text)
        assert len(obs) == 3
        assert obs[2]["theme"] == "acoustique_sia_181"

    def test_empty_or_short_text_returns_empty(self) -> None:
        assert _parse_observations("") == []
        assert _parse_observations("trop court") == []

    def test_unrecognized_format_returns_empty(self) -> None:
        """Texte sans structure numérotée ne doit rien retourner (fallback amont)."""
        text = "Ceci est un simple paragraphe sans numérotation ni structure."
        assert _parse_observations(text) == []

    def test_classify_theme_keywords(self) -> None:
        assert _classify_theme("le calcul sia 380/1 est manquant") == "energie_sia_380_1"
        assert _classify_theme("compartimentage feu entre étages") == "incendie_aeai"
        assert _classify_theme("indice ibus trop élevé") == "gabarit_zone"
        assert _classify_theme("ldtr et loyer contrôlé") == "ldtr"

    def test_classify_theme_fallback_general(self) -> None:
        assert _classify_theme("texte sans mot-clé reconnu du tout") == "general"

    def test_all_thematic_keywords_have_content(self) -> None:
        for theme, keywords in THEMATIC_KEYWORDS.items():
            assert len(keywords) >= 2, f"Thème {theme} n'a que {len(keywords)} mots-clés"
            assert all(isinstance(k, str) and k for k in keywords)
