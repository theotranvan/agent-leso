"""Tests basiques de smoke pour valider que l'app démarre."""
import pytest


def test_config_loads():
    from app.config import settings
    assert settings.ENVIRONMENT == "development"
    assert settings.RATE_LIMIT_PER_MINUTE == 100


def test_routing_table_complete():
    from app.agent.router import ROUTING_TABLE, MODEL_HAIKU, MODEL_OPUS, MODEL_SONNET
    # Vérifie que tous les modèles sont représentés
    assert MODEL_OPUS in ROUTING_TABLE.values()
    assert MODEL_SONNET in ROUTING_TABLE.values()
    assert MODEL_HAIKU in ROUTING_TABLE.values()
    # Tâches critiques bien sur Opus
    assert ROUTING_TABLE["note_calcul_structure"] == MODEL_OPUS
    assert ROUTING_TABLE["calcul_thermique_re2020"] == MODEL_OPUS


def test_prompts_exist():
    from app.agent.prompts import PROMPTS, get_system_prompt
    assert len(PROMPTS) >= 10
    assert "cctp" in get_system_prompt("redaction_cctp").lower() or "CCTP" in get_system_prompt("redaction_cctp")


def test_cost_estimation():
    from app.agent.router import estimate_cost_eur, MODEL_SONNET
    cost = estimate_cost_eur(MODEL_SONNET, 1_000_000, 500_000)
    # 3$ input + 7.5$ output = 10.5$ ≈ 9.66€
    assert 5 < cost < 15


def test_chunking():
    from app.services.embeddings import chunk_text
    text = "Paragraphe 1.\n\n" + ("Lorem ipsum. " * 200) + "\n\nParagraphe 3."
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) >= 1
    for c in chunks:
        assert c.strip()


def test_markdown_to_html():
    from app.services.pdf_generator import markdown_to_html
    md = "# Titre\n\n**Gras** et *italique*.\n\n- Item 1\n- Item 2"
    html = markdown_to_html(md)
    assert "<h1>Titre</h1>" in html
    assert "<strong>Gras</strong>" in html
    assert "<li>Item 1</li>" in html


def test_bcf_generation():
    from app.services.ifc_parser import generate_bcf_xml
    clashes = [
        {
            "element_a": {"lot": "cvc", "type": "IfcDuct", "name": "Gaine 1", "id": "abc"},
            "element_b": {"lot": "structure", "type": "IfcBeam", "name": "Poutre 1", "id": "def"},
        }
    ]
    xml = generate_bcf_xml(clashes, project_name="Test")
    assert "<?xml" in xml
    assert "Clash" in xml
    assert "cvc" in xml
