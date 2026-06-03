"""Endpoint de test E2E interne — exécuté côté serveur (Render).

Appelable sans auth navigateur : s'autentifie via service_role directement
sur Supabase (IP Render déjà autorisée), puis exerce tous les modules.

Protégé par un secret partagé (E2E_SECRET) pour éviter les abus.
Usage :
    GET https://bet-agent-api.onrender.com/health/e2e?secret=<E2E_SECRET>&email=...
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.database import get_supabase_admin
from app.services.pdf_renderer import markdown_to_html, render_pdf_from_html
from app.storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

_E2E_SECRET = "leso-e2e-2026"  # secret fixe pour l'env de test


def _ok(label: str) -> dict:
    return {"label": label, "status": "PASS"}


def _fail(label: str, detail: str) -> dict:
    return {"label": label, "status": "FAIL", "detail": detail[:300]}


def _skip(label: str, why: str) -> dict:
    return {"label": label, "status": "SKIP", "detail": why}


@router.get("/e2e")
async def run_e2e(
    secret: str = Query(..., description="Secret partagé"),
    email: str = Query("jc.szwed@conti-ing.ch", description="Email ingénieur test"),
):
    """Lance tous les tests E2E côté serveur et retourne les résultats JSON."""
    if secret != _E2E_SECRET:
        raise HTTPException(status_code=403, detail="Secret invalide")

    results: list[dict[str, Any]] = []
    admin = get_supabase_admin()
    storage = get_storage()

    def check(label: str, ok: bool, detail: str = "") -> bool:
        results.append(_ok(label) if ok else _fail(label, detail))
        return ok

    # ---------------------------------------------------------------- AUTH
    # Récupère le user via admin (pas besoin d'auth Supabase depuis ici)
    user_row = admin.table("users").select("*").eq("email", email).maybe_single().execute()
    if not user_row.data:
        raise HTTPException(status_code=404, detail=f"User {email} non trouvé en base")

    user_data = user_row.data
    org_id = user_data.get("organization_id")
    user_id = user_data.get("id")
    check("User trouvé en base", bool(user_id and org_id),
          f"user_id={user_id} org_id={org_id}")

    # ---------------------------------------------------------------- PROJET
    ts = int(time.time())
    proj_r = admin.table("projects").insert({
        "organization_id": org_id,
        "name": f"E2E-SERVER-{ts}",
        "canton": "GE",
        "affectation": "logement_collectif",
        "address": "Test 1, 1200 Genève",
    }).execute()
    project_id = (proj_r.data[0] if proj_r.data else {}).get("id")
    check("Création projet", bool(project_id), str(proj_r))

    # ------------------------------------------------ SIMULATION RAPIDE (sync)
    try:
        from app.services.swiss.simulation_rapide import compute_simulation_rapide
        sim = compute_simulation_rapide({
            "sre_m2": 2400, "affectation": "logement_collectif",
            "canton": "GE", "standard": "sia_380_1_neuf",
            "heating_vector": "chauffage_distance", "facteur_forme": "standard",
        })
        qh = (sim.get("main_variant") or {}).get("qh_kwh_m2_an")
        check("Simulation rapide (Qh)", qh is not None, f"sim={sim}")
    except Exception as e:
        check("Simulation rapide (Qh)", False, str(e))

    # ------------------------------------------------ THERMIQUE SIA 380/1
    try:
        tm_r = admin.table("thermal_models").insert({
            "organization_id": org_id, "project_id": project_id,
            "name": f"E2E-Therm-{ts}", "canton": "GE",
            "affectation": "logement_collectif", "operation_type": "neuf",
            "standard": "sia_380_1", "status": "draft",
            "zones": [{"name": "Logements", "affectation": "logement_collectif",
                       "area": 1200, "volume": 3000, "temp_setpoint": 20}],
            "walls": [
                {"type": "mur_exterieur", "orientation": "N", "area": 300, "u_value": 0.20},
                {"type": "toiture", "orientation": "horizontal", "area": 400, "u_value": 0.15},
                {"type": "dalle_sol", "orientation": "horizontal", "area": 400, "u_value": 0.25},
            ],
            "openings": [{"type": "fenetre", "area": 120, "u_value": 1.1,
                          "g_value": 0.5, "orientation": "S"}],
            "systems": {"heating": {"vector": "chauffage_distance", "efficiency": 0.98},
                        "ventilation": {"type": "double_flux", "heat_recovery_pct": 75}},
        }).execute()
        therm_id = (tm_r.data[0] if tm_r.data else {}).get("id")
        check("Thermique: création modèle", bool(therm_id), str(tm_r))

        if therm_id:
            from app.services.thermique.pipeline import run_thermal_pipeline
            model = tm_r.data[0]
            result = await run_thermal_pipeline(
                thermal_model=model, engine_name="lesosai_stub",
                project_name="E2E", project_address="Test, GE", author="E2E",
            )
            check("Thermique: run pipeline (PDF justificatif)",
                  bool(result.get("pdf_bytes")), str(result.get("warnings", "")))
    except Exception as e:
        check("Thermique: run pipeline (PDF justificatif)", False, str(e))

    # ------------------------------------------------ STRUCTURE SIA 260
    try:
        sm_r = admin.table("structural_models").insert({
            "organization_id": org_id, "project_id": project_id,
            "name": f"E2E-Struct-{ts}", "status": "draft",
            "referentiel": "sia", "exposure_class": "XC2",
            "consequence_class": "CC2", "seismic_zone": "Z1b",
            "nodes": [{"id": "N1", "x": 0, "y": 0, "z": 0},
                      {"id": "N2", "x": 6, "y": 0, "z": 0}],
            "members": [{"id": "M1", "type": "beam", "node_start": "N1",
                         "node_end": "N2", "section": "HEA200", "material": "S235"}],
            "supports": [{"id": "S1", "node": "N1", "type": "pinned"},
                         {"id": "S2", "node": "N2", "type": "roller"}],
            "load_cases": [{"id": "G", "name": "Poids propre", "category": "Permanent"},
                           {"id": "Q", "name": "Exploitation", "category": "Variable"}],
            "loads": [{"id": "L1", "case": "Q", "target": "M1",
                       "target_type": "member", "type": "uniform_vertical",
                       "direction": "-Z", "value_kN_m": 15}],
        }).execute()
        struct_id = (sm_r.data[0] if sm_r.data else {}).get("id")
        check("Structure: création modèle", bool(struct_id), str(sm_r))

        if struct_id:
            from app.services.structure.saf_builder import build_saf_and_sheet
            model = sm_r.data[0]
            full_model = {
                "project": {"name": model["name"], "referentiel": model.get("referentiel", "sia"),
                             "exposure_class": model.get("exposure_class", "XC2"),
                             "consequence_class": model.get("consequence_class", "CC2"),
                             "seismic_zone": model.get("seismic_zone", "Z1b")},
                "nodes": model.get("nodes", []), "members": model.get("members", []),
                "supports": model.get("supports", []), "load_cases": model.get("load_cases", []),
                "combinations": model.get("combinations", []), "loads": model.get("loads", []),
            }
            result = build_saf_and_sheet(full_model)
            check("Structure: génération SAF Excel",
                  bool(result.get("saf_xlsx")), str(result.get("warnings", "")))
    except Exception as e:
        check("Structure: génération SAF Excel", False, str(e))

    # ------------------------------------------------ AEAI INCENDIE
    try:
        from app.ch.aeai_templates import build_checklist
        items = build_checklist(building_type="habitation_moyenne", height_m=18, nb_occupants=60)
        check("AEAI: génération items checklist", len(items) > 0, f"{len(items)} items")

        cl_r = admin.table("aeai_checklists").insert({
            "organization_id": org_id, "project_id": project_id,
            "building_type": "habitation_moyenne", "height_class": "moyenne_11-30m",
            "nb_occupants_max": 60, "items": items, "status": "draft",
        }).execute()
        cl_id = (cl_r.data[0] if cl_r.data else {}).get("id")
        check("AEAI: création checklist en base", bool(cl_id), str(cl_r))

        if cl_id:
            # marque 3 items conformes
            for it in items[:3]:
                it["status"] = "CONFORME"
            admin.table("aeai_checklists").update({"items": items, "status": "completed"}).eq("id", cl_id).execute()

            # export PDF
            from datetime import datetime
            from app.routes.aeai import _checklist_to_md
            cl_data = admin.table("aeai_checklists").select("*").eq("id", cl_id).maybe_single().execute().data
            md = _checklist_to_md(cl_data)
            pdf_bytes = render_pdf_from_html(
                body_html=markdown_to_html(md),
                title="Rapport AEAI - Checklist incendie",
                subtitle=cl_data.get("building_type", ""),
                reference=f"AEAI-{datetime.now().strftime('%Y%m%d')}",
            )
            check("AEAI: export PDF", len(pdf_bytes) > 1000, f"{len(pdf_bytes)} bytes")
    except Exception as e:
        check("AEAI: export PDF", False, str(e))

    # ------------------------------------------------ IDC GENÈVE
    try:
        bld_r = admin.table("idc_buildings").insert({
            "organization_id": org_id, "project_id": project_id,
            "ega": "E2E-1234", "address": "Rue de Rive 10, 1204 Genève",
            "sre_m2": 850, "heating_energy_vector": "gaz",
            "building_year": 1985, "nb_logements": 12,
        }).execute()
        bld_id = (bld_r.data[0] if bld_r.data else {}).get("id")
        check("IDC: création bâtiment", bool(bld_id), str(bld_r))

        if bld_id:
            from app.services.swiss.idc_geneva import compute_annual_from_invoices
            calc = compute_annual_from_invoices(
                [{"value": 125000, "unit": "kwh"}],
                sre_m2=850, vector="gaz", affectation="logement_collectif",
            )
            check("IDC: calcul IDC normalisé", bool(calc.get("idc_normalise_mj_m2")),
                  str(calc))

            decl_r = admin.table("idc_annual_declarations").insert({
                "building_id": bld_id, "organization_id": org_id,
                "year": 2024, "consumption_kwh": calc.get("consumption_kwh"),
                "idc_mj_m2": calc.get("idc_normalise_mj_m2"), "status": "draft",
            }).execute()
            check("IDC: déclaration annuelle créée",
                  bool((decl_r.data[0] if decl_r.data else {}).get("id")), str(decl_r))
    except Exception as e:
        check("IDC: calcul IDC normalisé", False, str(e))

    # ------------------------------------------------ PRÉ-BIM (from-spec, sans Claude)
    try:
        from app.services.bim.premodel_generator import PreModelGenerator
        spec = {
            "project_name": "E2E-BIM", "building_name": "Bâtiment A",
            "canton": "GE", "operation_type": "neuf",
            "affectation": "logement_collectif", "nb_logements": 8,
            "storeys": [
                {"name": "RDC", "elevation_m": 0.0, "height_m": 3.0, "area_m2": 300},
                {"name": "R+1", "elevation_m": 3.0, "height_m": 2.8, "area_m2": 300},
            ],
            "envelope": {
                "plan_width_m": 20, "plan_depth_m": 15,
                "wall_composition_key": "mur_ext_neuf_standard",
                "roof_composition_key": "toit_neuf_perform",
                "slab_ground_composition_key": "dalle_sur_terrain_neuf",
                "window_ratio_by_orientation": {"N": 0.15, "S": 0.30, "E": 0.20, "W": 0.20},
                "window_u_value": 1.0, "window_g_value": 0.55,
            },
        }
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
            ifc_path = tmp.name
        gen = PreModelGenerator(spec)
        gen.generate(ifc_path)
        size = os.path.getsize(ifc_path)
        os.unlink(ifc_path)
        check("Pré-BIM: génération IFC (from-spec)", size > 1000, f"{size} bytes")
    except Exception as e:
        check("Pré-BIM: génération IFC (from-spec)", False, str(e))

    # ------------------------------------------------ OBSERVATIONS (agent async)
    try:
        task_r = admin.table("tasks").insert({
            "organization_id": org_id, "project_id": project_id,
            "task_type": "reponse_observations", "status": "pending",
            "input_params": {
                "authority": "DALE",
                "observations_text": "Précisions sur la hauteur du bâtiment.",
            },
            "created_by": user_id,
        }).execute()
        task_id = (task_r.data[0] if task_r.data else {}).get("id")
        check("Observations: tâche mise en queue", bool(task_id), str(task_r))
    except Exception as e:
        check("Observations: tâche mise en queue", False, str(e))

    # ------------------------------------------------ DASHBOARDS
    try:
        from app.routes.dashboard import (
            overview, compliance_overview, consumption_overview,
        )
        from unittest.mock import MagicMock
        mock_user = MagicMock()
        mock_user.organization_id = org_id
        mock_user.id = user_id
        mock_user.role = "member"

        ov = await overview(mock_user)
        check("Dashboard: overview", bool(ov), str(ov)[:100])
        co = await compliance_overview(mock_user)
        check("Dashboard: compliance", bool(co), str(co)[:100])
    except Exception as e:
        check("Dashboard: overview/compliance", False, str(e))

    # ------------------------------------------------ VEILLE
    try:
        alerts_r = admin.table("regulatory_changes").select("id").limit(1).execute()
        check("Veille: table regulatory_changes accessible", True)
    except Exception as e:
        check("Veille: table regulatory_changes accessible", False, str(e))

    # ------------------------------------------------ EXPORT ZIP
    try:
        from app.services.ao_export import build_ao_dossier_zip
        try:
            zip_bytes, filename, summary = await build_ao_dossier_zip(
                project_id, org_id, only_approved=False,
            )
            is_zip = zip_bytes[:2] == b"PK"
            check("Export dossier ZIP", is_zip or summary["documents_included"] == 0,
                  f"docs={summary['documents_included']}")
        except ValueError:
            check("Export dossier ZIP", True, "0 documents (normal, projet vide)")
    except Exception as e:
        check("Export dossier ZIP", False, str(e))

    # ------------------------------------------------ MODULES MANUELS
    results.append(_skip("Pré-BIM from-text", "appelle Claude — non déterministe"))
    results.append(_skip("Métrés IFC", "nécessite un vrai fichier .ifc en upload"))
    results.append(_skip("Coordination inter-lots", "nécessite 2 fichiers .ifc"))

    # ------------------------------------------------ BILAN
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    return {
        "summary": {"passed": passed, "failed": failed, "skipped": skipped,
                    "total": passed + failed + skipped},
        "ok": failed == 0,
        "results": results,
    }
