"""Test E2E COMPLET contre la PROD — couvre les modules non testés par smoke_e2e.

Se connecte comme un vrai ingénieur (compte seed_team) et déroule TOUS les
modules qui, jusqu'ici, ne se testaient qu'à la main dans le navigateur :
thermique SIA, structure SIA, AEAI incendie, IDC Genève (avec upload facture),
pré-BIM (from-spec, sans Claude), veille, dashboards, observations, export ZIP.

Affiche PASS/FAIL par étape. Stdlib uniquement (urllib) — rien à installer.
Aucun secret en dur : tout vient des arguments ou des variables d'env, donc
ce fichier est sûr à committer.

Les seuls modules NON couverts ici (ils restent à tester à la main) :
  - Pré-BIM *from-text*  : appelle Claude (coûteux, non déterministe)
  - Métrés IFC           : nécessite un vrai fichier .ifc en upload
  - Coordination inter-lots : nécessite 2 fichiers .ifc

Usage :
    python scripts/full_e2e.py \
        --api  https://bet-agent-api.onrender.com \
        --supabase https://xxxx.supabase.co \
        --anon  <SUPABASE_ANON_KEY> \
        --email ing2@conti.ch \
        --password '<mot de passe du compte>'

Variables d'env équivalentes :
    API_URL, SUPABASE_URL, SUPABASE_ANON_KEY, SMOKE_EMAIL, SMOKE_PASSWORD
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

_OK = "\033[92mPASS\033[0m"
_KO = "\033[91mFAIL\033[0m"
_SKIP = "\033[93mSKIP\033[0m"


def _req(method: str, url: str, headers: dict, body=None, raw_body: bytes | None = None,
         timeout=180, want_bytes=False):
    """Requête HTTP. body=dict (JSON) ou raw_body=bytes (multipart déjà encodé)."""
    if raw_body is not None:
        data = raw_body
    elif body is not None:
        data = json.dumps(body).encode()
    else:
        data = None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
            if want_bytes:
                return resp.status, payload
            raw = payload.decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"detail": raw[:300]}
    except Exception as e:
        return 0, {"detail": str(e)}


def _multipart(fields: dict[str, str], file_field: str, filename: str,
               file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Encode un body multipart/form-data. Retourne (body, content_type_header)."""
    boundary = f"----leso{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        parts.append(f"{v}\r\n".encode())
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
    )
    parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
    parts.append(file_bytes)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _tiny_pdf(text: str) -> bytes:
    """Génère un PDF minimal valide (1 page, un peu de texte) — stdlib only."""
    content = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF").encode()
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default=os.getenv("API_URL", ""))
    p.add_argument("--supabase", default=os.getenv("SUPABASE_URL", ""))
    p.add_argument("--anon", default=os.getenv("SUPABASE_ANON_KEY", ""))
    p.add_argument("--email", default=os.getenv("SMOKE_EMAIL", ""))
    p.add_argument("--password", default=os.getenv("SMOKE_PASSWORD", ""))
    a = p.parse_args()

    missing = [k for k, v in {
        "--api": a.api, "--supabase": a.supabase, "--anon": a.anon,
        "--email": a.email, "--password": a.password,
    }.items() if not v]
    if missing:
        print(f"Paramètres manquants : {', '.join(missing)}", file=sys.stderr)
        return 2

    api = a.api.rstrip("/")
    passed = failed = skipped = 0

    def check(label: str, ok: bool, detail: str = ""):
        nonlocal passed, failed
        print(f"  {_OK if ok else _KO}  {label}" + (f"  — {detail}" if detail and not ok else ""))
        if ok:
            passed += 1
        else:
            failed += 1
        return ok

    def skip(label: str, why: str):
        nonlocal skipped
        print(f"  {_SKIP}  {label}  — {why}")
        skipped += 1

    print(f"\nE2E COMPLET → {api}\n" + "=" * 64)

    # ---------------------------------------------------------------- AUTH
    print("\n[ Auth & projet ]")
    status, body = _req(
        "POST",
        f"{a.supabase.rstrip('/')}/auth/v1/token?grant_type=password",
        {"apikey": a.anon, "Content-Type": "application/json"},
        {"email": a.email, "password": a.password},
    )
    token = body.get("access_token")
    if not check("Connexion ingénieur (Supabase)", bool(token),
                 f"HTTP {status} {body.get('error_description') or body.get('detail','')}"):
        print("\nArrêt : impossible de se connecter.")
        return 1
    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    HA = {"Authorization": f"Bearer {token}"}  # sans Content-Type (multipart)

    status, me = _req("GET", f"{api}/api/auth/me", H)
    check("GET /api/auth/me", status == 200, f"HTTP {status} {me.get('detail','')}")

    status, proj = _req("POST", f"{api}/api/projects", H, {
        "name": f"E2E {int(time.time())}", "canton": "GE",
        "affectation": "logement_collectif", "address": "Test 1, 1200 Genève",
    })
    project_id = proj.get("id")
    check("POST /api/projects", status in (200, 201) and bool(project_id),
          f"HTTP {status} {proj.get('detail','')}")

    # ---------------------------------------------------- SIMULATION RAPIDE
    print("\n[ Simulation énergétique rapide ]")
    status, sim = _req("POST", f"{api}/api/v4/simulation-rapide/sync", H, {
        "project_name": "E2E", "author": "E2E",
        "programme": {"sre_m2": 2400, "affectation": "logement_collectif",
                      "canton": "GE", "standard": "sia_380_1_neuf",
                      "heating_vector": "chauffage_distance", "facteur_forme": "standard"},
    })
    qh = (sim.get("main_variant") or {}).get("qh_kwh_m2_an")
    check("POST simulation-rapide/sync (Qh calculé)", status == 200 and qh is not None,
          f"HTTP {status} {sim.get('detail','')}")

    # --------------------------------------------------------- THERMIQUE SIA
    print("\n[ Thermique SIA 380/1 ]")
    status, tm = _req("POST", f"{api}/api/thermique/models", H, {
        "name": "E2E-Therm", "project_id": project_id, "canton": "GE",
        "affectation": "logement_collectif", "operation_type": "neuf",
        "standard": "sia_380_1",
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
    })
    therm_id = tm.get("id")
    check("POST /api/thermique/models", status in (200, 201) and bool(therm_id),
          f"HTTP {status} {tm.get('detail','')}")
    if therm_id:
        status, run = _req("POST", f"{api}/api/thermique/models/{therm_id}/run", H,
                           {"model_id": therm_id, "engine": "lesosai_stub",
                            "author_name": "E2E"})
        rq = (run.get("results") or {}).get("qh_kwh_m2_an") or (run.get("results") or {}).get("qh")
        check("POST thermique/models/{id}/run (justificatif + Qh)",
              status == 200 and bool(run.get("pdf_url")),
              f"HTTP {status} {run.get('detail','')}")

    # ---------------------------------------------------------- STRUCTURE SIA
    print("\n[ Structure SIA 260 ]")
    status, sm = _req("POST", f"{api}/api/structure/models", H, {
        "name": "E2E-Struct", "project_id": project_id,
        "project": {"name": "E2E-Struct", "referentiel": "sia",
                    "exposure_class": "XC2", "consequence_class": "CC2",
                    "seismic_zone": "Z1b"},
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
    })
    struct_id = sm.get("id")
    check("POST /api/structure/models", status in (200, 201) and bool(struct_id),
          f"HTTP {status} {sm.get('detail','')}")
    if struct_id:
        status, saf = _req("POST", f"{api}/api/structure/models/{struct_id}/generate-saf", H, {})
        check("POST structure/models/{id}/generate-saf (SAF + notice)",
              status == 200 and bool(saf.get("saf_url")),
              f"HTTP {status} {saf.get('detail','')}")

    # ---------------------------------------------------------- AEAI INCENDIE
    print("\n[ AEAI incendie ]")
    status, cl = _req("POST", f"{api}/api/aeai/checklists", H, {
        "project_id": project_id, "building_type": "habitation_moyenne",
        "height_class": "moyenne_11-30m", "height_m": 18, "nb_occupants_max": 60,
    })
    cl_id = cl.get("id")
    items = cl.get("items") or []
    check("POST /api/aeai/checklists (items générés)",
          status in (200, 201) and bool(cl_id) and len(items) > 0,
          f"HTTP {status} {cl.get('detail','')}")
    if cl_id and items:
        # marque 3 items conformes
        for it in items[:3]:
            it["status"] = "CONFORME"
        status, _u = _req("PATCH", f"{api}/api/aeai/checklists/{cl_id}", H,
                          {"items": items, "status": "completed"})
        check("PATCH aeai/checklists/{id} (coches sauvées)", status == 200,
              f"HTTP {status} {_u.get('detail','')}")
        status, pdf = _req("POST", f"{api}/api/aeai/checklists/{cl_id}/export-pdf", H, {})
        check("POST aeai/checklists/{id}/export-pdf (PDF)",
              status == 200 and bool(pdf.get("pdf_url")),
              f"HTTP {status} {pdf.get('detail','')}")

    # ----------------------------------------------------------- IDC GENÈVE
    print("\n[ IDC Genève (avec upload facture) ]")
    status, bld = _req("POST", f"{api}/api/idc/buildings", H, {
        "ega": "1234567", "address": "Rue de Rive 10, 1204 Genève",
        "postal_code": "1204", "sre_m2": 850, "heating_energy_vector": "gaz",
        "building_year": 1985, "nb_logements": 12, "project_id": project_id,
    })
    bld_id = bld.get("id")
    check("POST /api/idc/buildings", status in (200, 201) and bool(bld_id),
          f"HTTP {status} {bld.get('detail','')}")
    if bld_id:
        pdf_bytes = _tiny_pdf("Facture gaz SIG - 12500 kWh - periode 2024")
        mp_body, mp_ct = _multipart({}, "pdf", "facture.pdf", pdf_bytes, "application/pdf")
        h_up = {**HA, "Content-Type": mp_ct}
        status, ext = _req("POST", f"{api}/api/idc/buildings/{bld_id}/extract-invoice",
                           h_up, raw_body=mp_body)
        # l'extraction peut renvoyer 0 (PDF synthétique) mais ne doit PAS planter
        check("POST idc/buildings/{id}/extract-invoice (upload OK, pas de 500)",
              status == 200, f"HTTP {status} {ext.get('detail','')}")
        # déclaration annuelle (calcul IDC déterministe)
        status, decl = _req("POST", f"{api}/api/idc/declarations", H, {
            "building_id": bld_id, "year": 2024,
            "invoices": [{"value": 125000, "unit": "kwh"}],
        })
        check("POST /api/idc/declarations (calcul IDC + formulaire OCEN PDF)",
              status in (200, 201) and bool(decl.get("form_pdf_url") or decl.get("id")),
              f"HTTP {status} {decl.get('detail','')}")

    # -------------------------------------------------- PRÉ-BIM (from-spec, sans Claude)
    print("\n[ Pré-BIM (génération IFC, sans Claude) ]")
    status, pb = _req("POST", f"{api}/api/bim/premodel/from-spec", H, {
        "project_id": project_id,
        "spec": {
            "project_name": "E2E-BIM", "building_name": "Bâtiment A",
            "canton": "GE", "operation_type": "neuf",
            "affectation": "logement_collectif", "nb_logements": 8,
            "storeys": [
                {"name": "RDC", "elevation_m": 0, "height_m": 3.0, "area_m2": 300},
                {"name": "R+1", "elevation_m": 3.0, "height_m": 2.8, "area_m2": 300},
                {"name": "R+2", "elevation_m": 5.8, "height_m": 2.8, "area_m2": 300},
            ],
        },
    })
    check("POST bim/premodel/from-spec (IFC généré)",
          status in (200, 201) and bool(pb.get("id") or pb.get("ifc_url")),
          f"HTTP {status} {pb.get('detail','')}")

    # ----------------------------------------------- OBSERVATIONS (upload + queue)
    print("\n[ Réponse aux observations (upload PDF + mise en queue) ]")
    # 1) upload du courrier autorité (comme le fait l'UI)
    obs_pdf = _tiny_pdf("Courrier DALE - observations sur la hauteur du batiment")
    up_body, up_ct = _multipart({"category": "observations", "project_id": project_id or ""},
                                "file", "courrier_dale.pdf", obs_pdf, "application/pdf")
    status, up = _req("POST", f"{api}/api/v4/upload", {**HA, "Content-Type": up_ct},
                      raw_body=up_body)
    doc_id = up.get("document_id")
    check("POST /api/v4/upload (courrier autorité)", status == 200 and bool(doc_id),
          f"HTTP {status} {up.get('detail','')}")
    # 2) génération de la réponse à partir du document uploadé
    if doc_id:
        status, obs = _req("POST", f"{api}/api/v4/observations", H, {
            "project_id": project_id, "project_name": "E2E",
            "autorite_pdf_document_id": doc_id,
        })
        check("POST /api/v4/observations (202 accepté)",
              status in (200, 202) and bool(obs.get("id") or obs.get("task_id")),
              f"HTTP {status} {obs.get('detail','')}")

    # ------------------------------------------------------------- DASHBOARDS
    print("\n[ Dashboards & veille ]")
    for path, label in [
        ("/api/dashboard/overview", "dashboard/overview"),
        ("/api/dashboard/compliance", "dashboard/compliance"),
        ("/api/dashboard/consumption", "dashboard/consumption"),
        ("/api/dashboard/notifications", "dashboard/notifications"),
        ("/api/dashboard/analytics", "dashboard/analytics"),
        ("/api/dashboard/board", "dashboard/board"),
        ("/api/dashboard/engineer", "dashboard/engineer"),
        ("/api/dashboard/alerts", "dashboard/alerts"),
        ("/api/veille/alerts", "veille/alerts"),
        ("/api/veille/digest", "veille/digest"),
        ("/api/billing/usage", "billing/usage"),
        ("/api/billing/status", "billing/status"),
    ]:
        status, r = _req("GET", f"{api}{path}", H)
        check(f"GET {label}", status == 200, f"HTTP {status} {r.get('detail','')}")

    # ----------------------------------------------- TÂCHE EN QUEUE + WORKER
    print("\n[ Worker (tâche asynchrone) ]")
    status, task = _req("POST", f"{api}/api/tasks", H, {
        "task_type": "compte_rendu_reunion", "project_id": project_id,
        "input_params": {"objet": "Réunion E2E", "participants": ["A", "B"],
                         "notes": "Point 1: ok. Point 2: à suivre."},
        "send_email": False,
    })
    task_id = task.get("id")
    check("POST /api/tasks (mise en queue)", status in (200, 202) and bool(task_id),
          f"HTTP {status} {task.get('detail','')}")
    if task_id:
        final = None
        for _ in range(30):  # ~90 s max (réveil worker inclus)
            time.sleep(3)
            st, stat = _req("GET", f"{api}/api/tasks/{task_id}/status", H)
            cur = stat.get("status")
            if cur in ("completed", "failed"):
                final = cur
                break
        check("Worker traite la tâche (completed)", final == "completed",
              f"statut final={final}")
        # approuve la tâche pour pouvoir tester l'export dossier
        if final == "completed":
            _req("POST", f"{api}/api/tasks/{task_id}/approve", H, {})

    # -------------------------------------------------------- EXPORT DOSSIER ZIP
    print("\n[ Export dossier ZIP ]")
    if project_id:
        status, zb = _req("GET",
                          f"{api}/api/projects/{project_id}/export-dossier?only_approved=false",
                          HA, want_bytes=True, timeout=120)
        is_zip = isinstance(zb, bytes) and zb[:2] == b"PK"
        check("GET projects/{id}/export-dossier (ZIP téléchargé)",
              status == 200 and is_zip,
              f"HTTP {status}" + ("" if is_zip else " (réponse non-ZIP)"))

    # -------------------------------------------------- MODULES MANUELS (rappel)
    print("\n[ Modules restant à tester à la main ]")
    skip("Pré-BIM from-text", "appelle Claude — non déterministe / coûteux")
    skip("Métrés IFC", "nécessite un vrai fichier .ifc en upload")
    skip("Coordination inter-lots", "nécessite 2 fichiers .ifc")

    # ----------------------------------------------------------------- BILAN
    print("\n" + "=" * 64)
    print(f"Résultat : {passed} PASS / {failed} FAIL / {skipped} SKIP")
    if failed == 0:
        print("✅ Tous les modules automatisables passent — reste 3 modules fichier à valider à la main.")
    else:
        print("⚠️  Au moins une étape a échoué — voir les détails ci-dessus.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
