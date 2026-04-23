"""Tests du pipeline d'ingestion documents pour les agents CH."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.agent.ingestion import (
    TASK_DOCUMENT_REQUIREMENTS,
    IngestionResult,
    _match_project_documents,
)


class TestIngestionRequirements:
    def test_all_major_task_types_covered(self) -> None:
        expected = {
            "justificatif_sia_380_1",
            "note_calcul_sia_260_267",
            "descriptif_can_sia_451",
            "controle_reglementaire_geneve",
            "dossier_mise_enquete",
            "reponse_observations_autorite",
            "metres_automatiques_ifc",
        }
        missing = expected - set(TASK_DOCUMENT_REQUIREMENTS.keys())
        assert not missing, f"Task types sans requirements : {missing}"

    def test_all_requirements_have_expected_keys(self) -> None:
        required = {"required_types", "keywords", "max_documents"}
        for tt, reqs in TASK_DOCUMENT_REQUIREMENTS.items():
            assert set(reqs.keys()) >= required, f"{tt} manque {required - set(reqs.keys())}"
            assert isinstance(reqs["max_documents"], int) and reqs["max_documents"] > 0

    def test_metres_requires_ifc_only(self) -> None:
        reqs = TASK_DOCUMENT_REQUIREMENTS["metres_automatiques_ifc"]
        assert "ifc" in reqs["required_types"]


class TestIngestionResult:
    def test_merge_preserves_existing_params(self) -> None:
        r = IngestionResult()
        r.documents_attached = [{"id": "doc1", "filename": "test.ifc"}]
        r.auto_params = {"canton": "GE"}

        original = {"canton": "VD", "sre_m2": 1000}  # canton déjà fourni
        merged = r.merge_into(original)

        # canton existant non écrasé
        assert merged["canton"] == "VD"
        # nouveau param ajouté
        assert merged["sre_m2"] == 1000
        # documents ajoutés
        assert len(merged["existing_documents"]) == 1

    def test_merge_adds_rag_context(self) -> None:
        r = IngestionResult()
        r.rag_context = "Contexte RAG"
        merged = r.merge_into({})
        assert merged["rag_context"] == "Contexte RAG"

    def test_merge_accumulates_warnings(self) -> None:
        r = IngestionResult()
        r.warnings = ["w1"]
        merged = r.merge_into({"ingestion_warnings": ["w0"]})
        assert merged["ingestion_warnings"] == ["w0", "w1"]


class TestMatchProjectDocuments:
    def _build_mock_admin(self, docs: list[dict]) -> MagicMock:
        admin = MagicMock()
        result = MagicMock()
        result.data = docs
        chain = MagicMock()
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = result
        admin.table.return_value.select.return_value = chain
        return admin

    def test_returns_empty_when_max_zero(self) -> None:
        admin = self._build_mock_admin([])
        docs = _match_project_documents(
            admin=admin, org_id="org", project_id="proj",
            required_types=["pdf"], keywords=["test"], max_documents=0,
        )
        assert docs == []

    def test_filters_by_file_type(self) -> None:
        fake_docs = [
            {"id": "1", "filename": "model.ifc", "file_type": "ifc"},
            {"id": "2", "filename": "notes.pdf", "file_type": "pdf"},
            {"id": "3", "filename": "data.xlsx", "file_type": "xlsx"},
        ]
        admin = self._build_mock_admin(fake_docs)
        docs = _match_project_documents(
            admin=admin, org_id="org", project_id="proj",
            required_types=["ifc"], keywords=[], max_documents=10,
        )
        assert all(d["file_type"] == "ifc" for d in docs)
