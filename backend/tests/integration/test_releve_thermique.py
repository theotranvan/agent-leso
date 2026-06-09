"""Relevé thermique depuis plans 2D — pipeline (vision mockée).

On vérifie toute la mécanique : rendu PDF→image, appel vision (mocké),
parsing JSON par planche, AGRÉGATION par orientation, et génération du
livrable (PDF + result_html exportable en Word). La qualité de lecture
réelle (vision) est validée en prod ; ici on prouve que la tuyauterie tient.
"""
from __future__ import annotations

import asyncio
import json

import pytest


def _one_page_pdf() -> bytes:
    """PDF minimal 1 page."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Plan")
    return doc.tobytes()


class _Storage:
    def __init__(self, data: bytes):
        self._d = data

    def download(self, path):
        return self._d

    def upload(self, *a, **k):
        return "p"

    def get_signed_url(self, *a, **k):
        return "https://fake/p"


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, filename="plan.pdf"):
        self._filename = filename

    def __getattr__(self, n):
        return lambda *a, **k: self

    def execute(self):
        return _Result({"storage_path": "x.pdf", "filename": self._filename, "file_type": "pdf"})


class _SeqAdmin:
    """Renvoie un filename différent par appel (route la bonne réponse vision)."""
    def __init__(self, names):
        self._it = iter(names)

    def table(self, n):
        return _Query(next(self._it, "Toiture"))


_RESPONSES = {
    "Façade Sud-Ouest": {"plan_type": "facade", "orientation": "SO", "echelle": "1:100",
                         "surface_facade_brute_m2": 250, "surface_fenetres_m2": 45,
                         "confiance": "haute", "remarques": "cotes lisibles"},
    "Façade Nord-Est": {"plan_type": "facade", "orientation": "NE", "echelle": "1:100",
                        "surface_facade_brute_m2": 208, "surface_fenetres_m2": 30,
                        "confiance": "moyenne", "remarques": ""},
    "Etage": {"plan_type": "etage", "orientation": None, "sre_contribution_m2": 238,
              "ponts_thermiques": [{"type": "balcon", "longueur_m": 12}], "confiance": "moyenne"},
    "Toiture": {"plan_type": "toiture", "surface_toiture_m2": 238, "confiance": "haute"},
}


def _fake_llm():
    async def _fake(*args, **kwargs):
        uc = kwargs.get("user_content") or (args[2] if len(args) > 2 else "")
        label = ""
        if isinstance(uc, list):
            for b in uc:
                if b.get("type") == "text":
                    label = b["text"]
        payload = {"error": "non lu"}
        for k, v in _RESPONSES.items():
            if k in label:
                payload = v
                break
        return {"text": json.dumps(payload), "model": "claude-opus-4-6",
                "tokens_used": 300, "input_tokens": 200, "output_tokens": 100,
                "cost_eur": 0.02, "cost_chf": 0.02, "fallback_used": False}
    return _fake


def test_releve_thermique_pipeline(monkeypatch):
    from app.agent.swiss import releve_thermique_agent as ag

    names = ["Façade Sud-Ouest", "Façade Nord-Est", "Etage", "Toiture"]
    monkeypatch.setattr(ag, "call_llm", _fake_llm(), raising=True)
    monkeypatch.setattr(ag, "get_storage", lambda: _Storage(_one_page_pdf()), raising=True)
    monkeypatch.setattr(ag, "get_supabase_admin", lambda: _SeqAdmin(names), raising=True)

    docs = [{"document_id": f"d{i}"} for i in range(len(names))]
    result = asyncio.run(ag.execute({
        "id": "t-thermo", "organization_id": "org", "project_id": None,
        "task_type": "releve_thermique_2d",
        "input_params": {"project_name": "Les Peupliers", "canton": "GE", "plan_documents": docs},
    }))

    t = result["thermal_takeoff"]
    assert t["sre_m2"] == 238
    assert t["surface_toiture_m2"] == 238
    assert t["facades"]["SO"] == 250 and t["facades"]["NE"] == 208
    assert t["fenetres"]["SO"] == 45 and t["fenetres"]["NE"] == 30
    assert any(p["type"] == "balcon" for p in t["ponts_thermiques"])
    assert result.get("result_html") and result.get("preview")

    from app.services.docx_generator import html_to_docx_bytes
    b = html_to_docx_bytes(result["result_html"], title="Relevé")
    assert b[:2] == b"PK" and len(b) > 2000


def test_releve_no_documents_raises():
    from app.agent.swiss import releve_thermique_agent as ag
    with pytest.raises(ValueError):
        asyncio.run(ag.execute({"id": "t", "organization_id": "o", "input_params": {}}))
