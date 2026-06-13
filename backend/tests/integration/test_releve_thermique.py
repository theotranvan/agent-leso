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
    assert any("balcon" in p["type"].lower() for p in t["ponts_thermiques"])  # consolidé en famille canonique
    assert result.get("result_html") and result.get("preview")

    from app.services.docx_generator import html_to_docx_bytes
    b = html_to_docx_bytes(result["result_html"], title="Relevé")
    assert b[:2] == b"PK" and len(b) > 2000


def test_releve_no_documents_raises():
    from app.agent.swiss import releve_thermique_agent as ag
    with pytest.raises(ValueError):
        asyncio.run(ag.execute({"id": "t", "organization_id": "o", "input_params": {}}))


# ----------------------------------------------------------------------------
# Lecture CAO (DXF) — MESURE géométrique (pas de vision)
# ----------------------------------------------------------------------------
def _facade_dxf() -> bytes:
    """DXF façade : murs 20×12 m (mm) + 3 fenêtres (blocs)."""
    import io

    import ezdxf
    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4  # mm
    doc.layers.add("101 - Eléments porteurs")
    doc.layers.add("201 - Fenetres")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (20000, 0), (20000, 12000), (0, 12000)],
                       close=True, dxfattribs={"layer": "101 - Eléments porteurs"})
    blk = doc.blocks.new(name="FENETRE")
    blk.add_lwpolyline([(0, 0), (1500, 0), (1500, 1400), (0, 1400)], close=True)
    for x in (2000, 6000, 10000):
        msp.add_blockref("FENETRE", (x, 3000), dxfattribs={"layer": "201 - Fenetres"})
    s = io.StringIO()
    doc.write(s)
    return s.getvalue().encode("utf-8")


def test_dxf_takeoff_unit():
    from app.services.cad.dxf_takeoff import extract_from_dxf
    r = extract_from_dxf(_facade_dxf(), "227 Façade Sud-Ouest.dxf")
    assert r["plan_type"] == "facade" and r["orientation"] == "SO"
    assert r["surface_facade_brute_m2"] == 240.0
    assert r["surface_fenetres_m2"] == 6.3  # 3 × 1.5×1.4
    assert r["methode"].startswith("mesure CAO")
    # pas de numpy qui fuit
    assert isinstance(r["surface_facade_brute_m2"], float)


def test_detect_plan_type_accents_nfd():
    """Noms de fichiers macOS (NFD, accents décomposés) — bug prod « Choulex ».

    « Façade »/« étage » y sont stockés avec un caractère combinant séparé : sans
    normalisation, le plan retombe en « autre » → façade non mesurée, étage exclu
    de la SRE. On vérifie la classification sur les formes décomposées exactes.
    """
    import unicodedata

    from app.services.cad.dxf_takeoff import detect_plan_type

    def nfd(s: str) -> str:
        return unicodedata.normalize("NFD", s)

    assert detect_plan_type(nfd("Sud-ouest Façade.dwg")) == ("facade", "SO")
    assert detect_plan_type(nfd("Nord-est Façade.dwg")) == ("facade", "NE")
    assert detect_plan_type(nfd("1. 1er étage.dwg")) == ("etage", None)
    assert detect_plan_type(nfd("2. Attique.dwg")) == ("etage", None)
    assert detect_plan_type(nfd("0. Rez-de-chaussée.dwg")) == ("etage", None)
    assert detect_plan_type(nfd("-1. Sous-sol.dwg")) == ("sous_sol", None)
    assert detect_plan_type(nfd("3. Toiture.dwg")) == ("toiture", None)
    # Forme composée (NFC) : doit toujours marcher aussi.
    assert detect_plan_type("Sud-est Façade.dwg") == ("facade", "SE")


def test_geometry_in_paperspace_is_measured():
    """Géométrie placée en ESPACE PAPIER (modelspace vide) — classe de panne
    « 0 entité → DWG non converti ». Le repli sur les présentations doit
    rattraper la planche au lieu de l'abandonner.
    """
    import io

    import ezdxf

    from app.services.cad.dxf_takeoff import extract_from_dxf

    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 6  # m
    doc.layers.add("111 - Toiture")
    psp = doc.layout("Layout1")
    psp.add_lwpolyline([(0, 0), (8, 0), (8, 5), (0, 5)], close=True,
                       dxfattribs={"layer": "111 - Toiture"})
    s = io.StringIO()
    doc.write(s)

    assert sum(1 for _ in doc.modelspace()) == 0  # rien en modelspace
    r = extract_from_dxf(s.getvalue().encode("utf-8"), "3. Toiture.dwg")
    assert r["plan_type"] == "toiture"
    assert r["surface_toiture_m2"] == 40.0  # 8 × 5, lu en espace papier


class _CadQuery:
    """Renvoie un document CAO (DXF) pour le routage métrés."""
    def __getattr__(self, n):
        return lambda *a, **k: self

    def execute(self):
        return _Result({"storage_path": "x.dxf", "filename": "227 Façade Sud-Ouest.dxf",
                        "file_type": "cad"})


class _CadAdmin:
    def table(self, n):
        return _CadQuery()


def test_metres_non_ifc_delegates_to_takeoff(monkeypatch):
    """Un DXF sur la tuile « Métrés » → relevé de surfaces (pas de parsing IFC)."""
    from app.agent.swiss import metres_agent as mg
    from app.agent.swiss import releve_thermique_agent as ag

    monkeypatch.setattr(mg, "get_storage", lambda: _Storage(_facade_dxf()), raising=True)
    monkeypatch.setattr(mg, "get_supabase_admin", lambda: _CadAdmin(), raising=True)
    monkeypatch.setattr(ag, "get_storage", lambda: _Storage(_facade_dxf()), raising=True)
    monkeypatch.setattr(ag, "get_supabase_admin", lambda: _CadAdmin(), raising=True)

    # Vision complémentaire neutralisée (JSON vide) : la géométrie doit suffire.
    async def _empty_vision(*a, **k):
        return {"text": "{}", "model": "x", "tokens_used": 0, "cost_eur": 0}
    monkeypatch.setattr(ag, "call_llm", _empty_vision, raising=True)

    result = asyncio.run(mg.execute({
        "id": "t-metres", "organization_id": "o", "project_id": None,
        "task_type": "metres_automatiques_ifc",
        "input_params": {"project_name": "P", "ifc_document_id": "d0"},
    }))
    # On a bien le livrable du relevé thermique (surfaces mesurées), pas un métré IFC.
    assert "thermal_takeoff" in result
    assert result["thermal_takeoff"]["facades"]["SO"] == 240.0


def test_metres_multi_plans_delegates_to_takeoff(monkeypatch):
    """Plusieurs plans (plan_documents) sur la tuile Métrés → relevé agrégé."""
    from app.agent.swiss import metres_agent as mg
    from app.agent.swiss import releve_thermique_agent as ag

    monkeypatch.setattr(mg, "get_storage", lambda: _Storage(_facade_dxf()), raising=True)
    monkeypatch.setattr(mg, "get_supabase_admin", lambda: _CadAdmin(), raising=True)
    monkeypatch.setattr(ag, "get_storage", lambda: _Storage(_facade_dxf()), raising=True)
    monkeypatch.setattr(ag, "get_supabase_admin", lambda: _CadAdmin(), raising=True)

    async def _empty_vision(*a, **k):
        return {"text": "{}", "model": "x", "tokens_used": 0, "cost_eur": 0}
    monkeypatch.setattr(ag, "call_llm", _empty_vision, raising=True)

    result = asyncio.run(mg.execute({
        "id": "t-metres-multi", "organization_id": "o", "project_id": None,
        "task_type": "metres_automatiques_ifc",
        "input_params": {"project_name": "P", "plan_documents": [
            {"document_id": "d0"}, {"document_id": "d1"},
        ]},
    }))
    assert "thermal_takeoff" in result
    # Les 2 plans (même façade de test) sont AGRÉGÉS → 2 × 240 = 480 m².
    assert result["thermal_takeoff"]["facades"]["SO"] == 480.0


def test_releve_dxf_measured_not_vision(monkeypatch):
    """Un DXF est MESURÉ (géométrie), pas lu par vision."""
    from app.agent.swiss import releve_thermique_agent as ag

    # Hybride : la vision peut être appelée en complément, mais ses estimations
    # sont neutralisées ici (JSON vide) → les chiffres viennent de la GÉOMÉTRIE.
    async def _empty_vision(*a, **k):
        return {"text": "{}", "model": "x", "tokens_used": 0, "cost_eur": 0}
    monkeypatch.setattr(ag, "call_llm", _empty_vision, raising=True)
    monkeypatch.setattr(ag, "get_storage", lambda: _Storage(_facade_dxf()), raising=True)
    monkeypatch.setattr(ag, "get_supabase_admin",
                        lambda: _SeqAdmin(["227 Façade Sud-Ouest.dxf"]), raising=True)

    result = asyncio.run(ag.execute({
        "id": "t", "organization_id": "o", "project_id": None,
        "task_type": "releve_thermique_2d",
        "input_params": {"project_name": "P", "plan_documents": [{"document_id": "d0"}]},
    }))
    t = result["thermal_takeoff"]
    assert t["facades"]["SO"] == 240.0   # gabarit mesuré (géométrie), pas estimé
    assert t["fenetres"]["SO"] == 6.3    # fenêtres mesurées sur le calque dédié
