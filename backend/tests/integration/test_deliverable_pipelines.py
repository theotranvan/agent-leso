"""Smoke test des pipelines de livrables — aucun ne doit planter.

Pour chaque type de livrable, on exécute le pipeline COMPLET de l'agent
(`execute(task)`) avec LLM + stockage + base de données SIMULÉS. On ne valide
PAS la qualité du texte généré (c'est le rôle de l'étape « À valider »), mais on
prouve que toute la mécanique tient : lecture des champs, appel LLM, parsing,
génération PDF/Excel/HTML, assemblage, et retour d'un dict exploitable.

Couvre les livrables « texte → LLM → rendu → stockage » sans entrée binaire
(les livrables qui exigent un IFC/PDF réel — coordination, métrés, IDC sur
factures — sont hors de ce smoke et couverts ailleurs).
"""
from __future__ import annotations

import asyncio
import importlib
import json

import pytest

# ----------------------------------------------------------------------------
# Fakes : stockage + base
# ----------------------------------------------------------------------------

class _FakeStorage:
    def upload(self, path, data, content_type="application/octet-stream"):
        return path

    def get_signed_url(self, path, expires_in=3600):
        return f"https://fake.local/{path}"

    def download(self, path):
        return b""

    def delete(self, path):
        return None


class _Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Query:
    def __init__(self):
        self._mode = "select"
        self._payload = None
        self._single = False

    def select(self, *a, **k):
        self._mode = "select"
        return self

    def insert(self, row):
        self._mode = "insert"
        self._payload = row
        return self

    def update(self, row):
        self._mode = "update"
        self._payload = row
        return self

    def eq(self, *a, **k):
        return self

    def maybe_single(self):
        self._single = True
        return self

    def limit(self, n):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        if self._mode == "insert":
            row = dict(self._payload) if isinstance(self._payload, dict) else {}
            row.setdefault("id", "fake-doc-id")
            return _Result([row])
        if self._mode == "update":
            return _Result([])
        # select → vide (branding tombe sur DEFAULT, org_name "")
        return _Result(None if self._single else [], count=0)


class _FakeAdmin:
    def table(self, name):
        return _Query()

    def rpc(self, *a, **k):
        return _Query()


def _fake_llm_factory(text: str):
    async def _fake_llm(*args, **kwargs):
        return {
            "text": text,
            "model": "claude-sonnet-4-6",
            "tokens_used": 200,
            "input_tokens": 100,
            "output_tokens": 100,
            "cost_eur": 0.01,
            "cost_chf": 0.01,
            "fallback_used": False,
        }
    return _fake_llm


async def _noop_str(*args, **kwargs):
    return ""


async def _noop_dict(*args, **kwargs):
    return {}


def _patch_module(monkeypatch, module, llm_text: str):
    """Neutralise LLM/stockage/DB/RAG dans le namespace d'un module agent."""
    monkeypatch.setattr(module, "call_llm", _fake_llm_factory(llm_text), raising=False)
    monkeypatch.setattr(module, "get_storage", lambda: _FakeStorage(), raising=False)
    monkeypatch.setattr(module, "get_supabase_admin", lambda: _FakeAdmin(), raising=False)
    monkeypatch.setattr(module, "build_project_context", _noop_str, raising=False)
    monkeypatch.setattr(module, "get_project_summary", _noop_dict, raising=False)


# ----------------------------------------------------------------------------
# Textes LLM simulés par format attendu
# ----------------------------------------------------------------------------

_HTML = "<h2>CFC 230 — Production</h2><p>Prescription contextualisée.</p><ul><li>PAC air-eau</li></ul>"
_MD = "# Livrable\n\n## Section\n\nContenu rédigé.\n\n- point 1\n- point 2\n"
_JSON_DPGF = json.dumps({
    "lines": [
        {"is_section": True, "designation": "CFC 231 — Production de chaleur"},
        {"article": "231.110", "designation": "PAC air-eau", "unite": "kW",
         "quantite": 50, "prix_unitaire": 1700, "hypothese": "Selon SRE"},
    ],
    "hypotheses_globales": ["Puissance estimée selon SRE"],
    "taux_incertitude_pct": 15,
})
_JSON_DQE = json.dumps({
    "lots": {
        "chauffage": [
            {"article": "1.1", "designation": "PAC air-eau", "unite": "kW",
             "quantite": 50, "prix_unitaire": 1700},
        ],
    },
})


def _task(task_type: str, params: dict) -> dict:
    return {
        "id": "task-smoke-1",
        "organization_id": "org-smoke",
        "project_id": None,
        "task_type": task_type,
        "input_params": params,
    }


# ----------------------------------------------------------------------------
# Cas de livrables : (task_type, module_path, agent_attr, params, llm_text)
# ----------------------------------------------------------------------------

CASES = [
    ("redaction_cctp", "app.agent.modules.cctp", "execute",
     {"lot": "chauffage", "type_ouvrage": "PAC air-eau", "niveau_prestation": "standard",
      "surface": "500", "contraintes": "Accès difficile", "articles_libres": "Article sur mesure : robinetterie inox."},
     _HTML),

    ("compte_rendu_reunion", "app.agent.modules.rapport", "execute",
     {"objet": "Réunion de coordination", "notes": "Point sur le planning et les lots.",
      "participants": ["Ing. A", "Arch. B"], "date": "07.06.2026", "lieu": "Bureau Lausanne"},
     _MD),

    ("memoire_technique", "app.agent.modules.rapport", "execute",
     {"brief": "Appel d'offres CVC immeuble 18 logements à Genève."},
     _MD),

    ("resume_document", "app.agent.modules.rapport", "execute",
     {"content": "Texte long à résumer. " * 50},
     _MD),

    ("chiffrage_dpgf", "app.agent.modules.chiffrage", "execute",
     {"lot": "chauffage", "niveau_prestation": "standard", "metre_text": "Surface : 500 m²"},
     _JSON_DPGF),

    ("chiffrage_dqe", "app.agent.modules.chiffrage", "execute",
     {"lot": "chauffage", "metre_text": "Surface : 500 m²"},
     _JSON_DQE),

    ("controle_reglementaire_geneve", "app.agent.swiss.geneva_agent", "execute",
     {"project_data": {"canton": "GE", "address": "Rue X 1", "affectation": "logement_collectif",
                       "operation_type": "neuf", "sre_m2": 1000, "nb_logements": 18}},
     _MD),

    ("dossier_mise_enquete", "app.agent.swiss.dossier_enquete_agent", "execute",
     {"project_data": {"canton": "GE", "address": "Rue X 1", "affectation": "logement_collectif",
                       "operation_type": "neuf", "sre_m2": 1000, "nb_logements": 18},
      "specificities": "Parcelle en zone 3, proximité voie ferrée."},
     _MD),

    ("reponse_observations_autorite", "app.agent.swiss.observations_agent", "execute",
     {"observations_text": "L'autorité demande des précisions sur le concept énergétique et le stationnement.",
      "authority": "DALE", "project_context": {"canton": "GE", "sre_m2": 1000}},
     _MD),

    ("calcul_acoustique", "app.agent.modules.note_calcul", "execute",
     {"elements": "Dalle béton 24 cm, cloisons légères", "hypotheses": "Logements superposés",
      "localisation": "Suisse"},
     _MD),

    ("simulation_energetique_rapide", "app.agent.swiss.simulation_rapide_agent", "execute",
     {"sre_m2": 1000, "affectation": "logement_collectif", "canton": "GE",
      "standard": "sia_380_1_neuf", "heating_vector": "gaz", "facteur_forme": "compact"},
     _MD),

    ("aeai_checklist_generation", "app.agent.swiss.aeai_agent", "execute_checklist",
     {"building_type": "habitation_moyenne", "height_m": 18, "nb_occupants_max": 60,
      "special_context": "Parking souterrain", "canton": "GE"},
     _MD),
]

# Livrables qui produisent un fichier (PDF/Excel) — les autres renvoient des
# données (checklist) et n'ont pas d'artefact fichier.
_DATA_ONLY = {"aeai_checklist_generation"}

# Seule la checklist AEAI est une donnée pure (pas de document rédigé) ; tous les
# autres livrables — DQE inclus — exposent un result_html exportable en Word.
_NO_DOCX_HTML = {"aeai_checklist_generation"}


@pytest.mark.parametrize("task_type,module_path,attr,params,llm_text", CASES,
                         ids=[c[0] for c in CASES])
def test_deliverable_pipeline_does_not_crash(
    monkeypatch, task_type, module_path, attr, params, llm_text,
):
    module = importlib.import_module(module_path)

    # Patch le module de dispatch + la source app.database (imports tardifs).
    _patch_module(monkeypatch, module, llm_text)
    import app.database as dbmod
    monkeypatch.setattr(dbmod, "get_storage", lambda: _FakeStorage(), raising=False)
    monkeypatch.setattr(dbmod, "get_supabase_admin", lambda: _FakeAdmin(), raising=False)

    execute = getattr(module, attr)
    result = asyncio.run(execute(_task(task_type, params)))

    # Contrat minimal : dict avec un aperçu non vide.
    assert isinstance(result, dict), f"{task_type} ne retourne pas un dict"
    assert result.get("preview"), f"{task_type} sans preview"
    # Les livrables « fichier » exposent une URL, des octets email ou du HTML.
    if task_type not in _DATA_ONLY:
        assert (
            result.get("result_url") is not None
            or result.get("email_bytes") is not None
            or result.get("result_html") is not None
        ), f"{task_type} ne produit aucun artefact (url/bytes/html)"

    # Export Word : tout livrable « rédigé » doit exposer un result_html exploitable
    # par l'export .docx (sinon le bouton Word retombe sur l'aperçu = tronqué).
    if task_type not in _NO_DOCX_HTML:
        html = result.get("result_html")
        assert html, f"{task_type} n'expose pas de result_html (export Word tronqué)"
        from app.services.docx_generator import html_to_docx_bytes
        docx_bytes = html_to_docx_bytes(html, title=task_type)
        # En-tête .docx = archive zip (PK\\x03\\x04) ; preuve d'un fichier valide.
        assert docx_bytes[:2] == b"PK", f"{task_type} : export .docx invalide"
        assert len(docx_bytes) > 2000, f"{task_type} : export .docx court"


# ----------------------------------------------------------------------------
# Livrables à entrée binaire : IFC synthétique + factures inline
# ----------------------------------------------------------------------------

def _synthetic_ifc() -> bytes:
    """IFC minimal : 1 étage + 2 espaces à quantités connues."""
    import ifcopenshell
    import ifcopenshell.api

    f = ifcopenshell.api.run("project.create_file")
    proj = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name="SMOKE")
    ifcopenshell.api.run("unit.assign_unit", f)
    ifcopenshell.api.run("context.add_context", f, context_type="Model")
    site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="S")
    bld = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="B")
    storey = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="RDC")
    ifcopenshell.api.run("aggregate.assign_object", f, products=[site], relating_object=proj)
    ifcopenshell.api.run("aggregate.assign_object", f, products=[bld], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", f, products=[storey], relating_object=bld)
    for i, (gfa, nfa, nv) in enumerate([(120.0, 108.0, 336.0), (80.0, 72.0, 224.0)]):
        sp = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSpace", name=f"L{i}")
        ifcopenshell.api.run("aggregate.assign_object", f, products=[sp], relating_object=storey)
        qto = ifcopenshell.api.run("pset.add_qto", f, product=sp, name="Qto_SpaceBaseQuantities")
        ifcopenshell.api.run("pset.edit_qto", f, qto=qto, properties={
            "GrossFloorArea": gfa, "NetFloorArea": nfa, "NetVolume": nv})
    return f.to_string().encode("utf-8")


class _IfcStorage(_FakeStorage):
    def __init__(self, ifc_bytes: bytes):
        self._ifc = ifc_bytes

    def download(self, path):
        return self._ifc


class _DocAdmin(_FakeAdmin):
    """Comme _FakeAdmin mais renvoie une ligne documents sur select maybe_single."""
    def table(self, name):
        q = _Query()
        if name == "documents":
            orig = q.execute

            def _exec():
                if q._mode == "select" and q._single:
                    return _Result({"storage_path": "x.ifc", "filename": "lot.ifc",
                                    "organization_id": "org-smoke", "file_type": "ifc"})
                return orig()
            q.execute = _exec
        return q



def _assert_word_ok(result):
    """Le livrable expose un result_html convertible en Word fidèle, sans CSS."""
    from app.services.docx_generator import html_to_docx_bytes
    html = result.get("result_html")
    assert html, "pas de result_html (export Word tronqué)"
    b = html_to_docx_bytes(html, title="t")
    assert b[:2] == b"PK" and len(b) > 2000
    import io

    import docx
    txt = "\n".join(p.text for p in docx.Document(io.BytesIO(b)).paragraphs)
    assert "font-family" not in txt and "{" not in txt, "CSS recopié dans le Word"

def test_metres_pipeline_does_not_crash(monkeypatch):
    from app.agent.swiss import metres_agent
    storage = _IfcStorage(_synthetic_ifc())
    monkeypatch.setattr(metres_agent, "get_storage", lambda: storage, raising=False)
    monkeypatch.setattr(metres_agent, "get_supabase_admin", lambda: _FakeAdmin(), raising=False)
    result = asyncio.run(metres_agent.execute(_task(
        "metres_automatiques_ifc",
        {"ifc_storage_path": "x.ifc", "project_name": "Test"},
    )))
    assert isinstance(result, dict)
    assert result.get("preview")
    _assert_word_ok(result)


def test_coordination_pipeline_does_not_crash(monkeypatch):
    from app.agent.modules import coordination
    storage = _IfcStorage(_synthetic_ifc())
    monkeypatch.setattr(coordination, "call_llm", _fake_llm_factory(_MD), raising=False)
    monkeypatch.setattr(coordination, "get_storage", lambda: storage, raising=False)
    monkeypatch.setattr(coordination, "get_supabase_admin", lambda: _DocAdmin(), raising=False)
    monkeypatch.setattr(coordination, "get_project_summary", _noop_dict, raising=False)
    result = asyncio.run(coordination.execute(_task(
        "coordination_inter_lots",
        {"ifc_documents": [
            {"lot": "cvc", "document_id": "d1"},
            {"lot": "electricite", "document_id": "d2"},
        ]},
    )))
    assert isinstance(result, dict)
    assert result.get("preview")
    _assert_word_ok(result)


def test_idc_pipeline_does_not_crash(monkeypatch):
    from app.agent.swiss import idc_agent
    monkeypatch.setattr(idc_agent, "call_llm", _fake_llm_factory(_MD), raising=False)
    monkeypatch.setattr(idc_agent, "get_storage", lambda: _FakeStorage(), raising=False)
    monkeypatch.setattr(idc_agent, "get_supabase_admin", lambda: _FakeAdmin(), raising=False)
    result = asyncio.run(idc_agent.execute(_task(
        "idc_geneve_rapport",
        {"building": {"sre_m2": 1000, "heating_vector": "gaz", "egid": "123",
                      "address": "Rue X 1", "nb_logements": 18},
         "year": 2024,
         "consumptions": [{"value": 60000, "unit": "kwh"}]},
    )))
    assert isinstance(result, dict)
    assert result.get("preview")
    _assert_word_ok(result)
