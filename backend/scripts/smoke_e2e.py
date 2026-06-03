"""Smoke test end-to-end contre la PROD — à lancer depuis ta machine.

Se connecte comme un vrai ingénieur (un des comptes créés par seed_team) et
déroule le parcours complet, en affichant PASS/FAIL à chaque étape. Stdlib
uniquement (urllib) — aucune dépendance à installer.

Usage :
    python scripts/smoke_e2e.py \
        --api  https://bet-agent-api.onrender.com \
        --supabase https://xxxx.supabase.co \
        --anon  <SUPABASE_ANON_KEY> \
        --email ing2@conti.ch \
        --password '<mot de passe du compte>'

Les valeurs peuvent aussi venir des variables d'env :
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

_OK = "\033[92mPASS\033[0m"
_KO = "\033[91mFAIL\033[0m"


def _req(method: str, url: str, headers: dict, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"detail": raw}
    except Exception as e:
        return 0, {"detail": str(e)}


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
    passed = failed = 0

    def check(label: str, ok: bool, detail: str = ""):
        nonlocal passed, failed
        print(f"  {_OK if ok else _KO}  {label}" + (f"  — {detail}" if detail and not ok else ""))
        if ok:
            passed += 1
        else:
            failed += 1
        return ok

    print(f"\nSmoke E2E → {api}\n" + "-" * 60)

    # 1. Login Supabase (password grant) → JWT
    status, body = _req(
        "POST",
        f"{a.supabase.rstrip('/')}/auth/v1/token?grant_type=password",
        {"apikey": a.anon, "Content-Type": "application/json"},
        {"email": a.email, "password": a.password},
    )
    token = body.get("access_token")
    if not check("Connexion ingénieur (Supabase)", bool(token), f"HTTP {status} {body.get('error_description') or body.get('detail','')}"):
        print("\nArrêt : impossible de se connecter.")
        return 1
    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. /me
    status, me = _req("GET", f"{api}/api/auth/me", H)
    check("GET /api/auth/me (token accepté)", status == 200, f"HTTP {status} {me.get('detail','')}")
    org_id = (me.get("organization") or {}).get("id") or me.get("organization_id")

    # 3. Crée un projet
    status, proj = _req("POST", f"{api}/api/projects", H, {
        "name": f"SMOKE {int(time.time())}",
        "canton": "GE", "affectation": "logement_collectif",
        "address": "Test 1, 1200 Genève",
    })
    project_id = proj.get("id")
    check("POST /api/projects (création projet)", status in (200, 201) and bool(project_id), f"HTTP {status} {proj.get('detail','')}")

    # 4. Le projet apparaît dans la liste (lecture partagée org)
    status, lst = _req("GET", f"{api}/api/projects", H)
    ids = [x.get("id") for x in (lst.get("projects") or [])]
    check("GET /api/projects (projet visible)", status == 200 and project_id in ids, f"HTTP {status}")

    # 5. Simulation énergétique (synchrone) — le cas qui avait échoué
    status, sim = _req("POST", f"{api}/api/v4/simulation-rapide/sync", H, {
        "project_name": "SMOKE", "author": "Smoke",
        "programme": {"sre_m2": 2400, "affectation": "logement_collectif",
                      "canton": "GE", "standard": "sia_380_1_neuf",
                      "heating_vector": "chauffage_distance", "facteur_forme": "standard"},
    })
    qh = (sim.get("main_variant") or {}).get("qh_kwh_m2_an")
    check("POST simulation-rapide/sync (Qh calculé)", status == 200 and qh is not None, f"HTTP {status} {sim.get('detail','')}")

    # 6. Crée une tâche en queue (légère) et vérifie qu'elle progresse
    status, task = _req("POST", f"{api}/api/tasks", H, {
        "task_type": "compte_rendu_reunion", "project_id": project_id,
        "input_params": {"objet": "Réunion smoke", "participants": ["A", "B"],
                         "notes": "Point 1: ok. Point 2: à suivre."},
        "send_email": False,
    })
    task_id = task.get("id")
    check("POST /api/tasks (mise en queue)", status in (200, 202) and bool(task_id), f"HTTP {status} {task.get('detail','')}")

    if task_id:
        final = None
        for _ in range(20):  # ~60s max
            time.sleep(3)
            st, stat = _req("GET", f"{api}/api/tasks/{task_id}/status", H)
            cur = stat.get("status")
            if cur in ("completed", "failed"):
                final = cur
                break
        check("Worker traite la tâche (completed)", final == "completed",
              f"statut final={final} (si 'pending' → worker/Redis ; si 'failed' → voir la tâche)")

    print("-" * 60)
    print(f"Résultat : {passed} PASS / {failed} FAIL")
    if failed == 0:
        print("✅ Parcours complet OK — prêt pour l'équipe.")
    else:
        print("⚠️  Au moins une étape a échoué — voir les détails ci-dessus.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
