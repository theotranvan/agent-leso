"""Script autonome — crée l'org Conti + 8 membres directement via l'API Supabase.
Aucune dépendance sur app.config : seuls SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY.

Usage (Windows cmd) :
    set SUPABASE_URL=https://xxxx.supabase.co
    set SUPABASE_SERVICE_ROLE_KEY=eyJ...
    python scripts/create_conti_team.py

Usage (PowerShell) :
    $env:SUPABASE_URL="https://xxxx.supabase.co"
    $env:SUPABASE_SERVICE_ROLE_KEY="eyJ..."
    python scripts/create_conti_team.py
"""
import json
import os
import secrets
import string
import sys
import urllib.error
import urllib.request

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SERVICE_KEY  = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

if not SUPABASE_URL or not SERVICE_KEY:
    print("ERREUR : SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY sont requis.", file=sys.stderr)
    sys.exit(1)

EMAILS = [
    "jc.szwed@conti-ing.ch",
    "a.levaigneur@conti-ing.ch",
    "y.mazgarean@conti-ing.ch",
    "e.stampfli@conti-ing.ch",
    "p.treboux@conti-ing.ch",
    "h.rychtarik@conti-ing.ch",
    "a.hurtic@conti-ing.ch",
    "m.levrier@conti-ing.ch",
]

NAMES = [
    "Jean-Christophe Szwed",
    "Achille Levaigneur",
    "Yann Mazgarean",
    "Etienne Stampfli",
    "Pauline Treboux",
    "Herve Rychtarik",
    "Adnan Hurtic",
    "Maxim Levrier",
]

H = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}


def _req(method, url, body=None, extra_headers=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {**H, **(extra_headers or {})}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw}


def gen_password():
    alpha = string.ascii_letters + string.digits
    pw = "".join(secrets.choice(alpha) for _ in range(14))
    return pw + secrets.choice("!@#$%") + secrets.choice(string.digits)


# 1. Créer ou récupérer l'organisation
print("→ Organisation Conti...")
status, orgs = _req("GET", f"{SUPABASE_URL}/rest/v1/organizations?name=eq.Conti&select=id")
if status == 200 and orgs:
    org_id = orgs[0]["id"]
    print(f"  déjà existante : {org_id}")
else:
    status, org = _req("POST", f"{SUPABASE_URL}/rest/v1/organizations",
        {"name": "Conti", "email": EMAILS[0], "plan": "starter",
         "tasks_limit": 500, "country": "CH", "language": "fr",
         "currency": "CHF", "vat_rate": 8.10},
        {"Prefer": "return=representation"})
    if status not in (200, 201):
        print(f"  ERREUR création org : {org}", file=sys.stderr)
        sys.exit(1)
    org_id = (org[0] if isinstance(org, list) else org)["id"]
    print(f"  créée : {org_id}")

# 2. Créer les 8 utilisateurs
results = []
for email, name in zip(EMAILS, NAMES):
    password = gen_password()

    # Créer dans auth.users
    status, user = _req("POST", f"{SUPABASE_URL}/auth/v1/admin/users", {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"full_name": name},
    })

    if status in (200, 201):
        user_id = user.get("id")
        # Insérer dans la table users publique
        _req("POST", f"{SUPABASE_URL}/rest/v1/users",
            {"id": user_id, "organization_id": org_id, "role": "member", "full_name": name},
            {"Prefer": "return=minimal"})
        results.append({"email": email, "password": password, "status": "créé"})
    elif status == 422 and "already" in str(user).lower():
        results.append({"email": email, "password": "— compte existant —", "status": "existe déjà"})
    else:
        results.append({"email": email, "password": "ERREUR", "status": str(user)})

# 3. Afficher le tableau récap
print("\n" + "=" * 74)
print(f"ÉQUIPE CONTI — org_id: {org_id}")
print("=" * 74)
print(f"{'EMAIL':<36}{'MOT DE PASSE':<22}STATUT")
print("-" * 74)
for r in results:
    print(f"{r['email']:<36}{r['password']:<22}{r['status']}")
print("=" * 74)
print("⚠  Distribuez ces mots de passe de façon sécurisée.")
print("   Chaque ingénieur peut changer son mot de passe depuis son profil.")
