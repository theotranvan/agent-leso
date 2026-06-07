"""Crée une organisation + son équipe d'un coup, sans passer par les invitations email.

Pour Conti : 1 organisation, 8 ingénieurs, tous avec accès au même espace
(mêmes projets). Le 1er user est admin (peut gérer l'équipe), les autres sont
membres (peuvent créer projets/tâches — accès complet de travail).

Usage :
    # 1) Renseigner les emails (1 par ligne) dans un fichier, OU via --emails
    python -m scripts.seed_team --org "Conti" --emails "a@conti.ch,b@conti.ch,..."
    python -m scripts.seed_team --org "Conti" --emails-file scripts/team.txt

Comportement :
    - Idempotent : un email déjà existant est ignoré (reporté), pas recréé.
    - Réutilise l'organisation existante si une porte déjà le même nom.
    - Génère un mot de passe fort par user et AFFICHE le tableau récap à la fin
      (à distribuer aux ingénieurs ; aucun secret n'est stocké dans le repo).
    - email_confirm=True → connexion immédiate, sans email de confirmation.

Nécessite les variables d'env standard (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
etc.) — les mêmes que l'API. À lancer depuis le dossier backend/.
"""
from __future__ import annotations

import argparse
import secrets
import string
import sys

from app.config import settings
from app.database import get_supabase_admin


def _gen_password(length: int = 16) -> str:
    """Mot de passe fort lisible (lettres + chiffres + 2 symboles sûrs)."""
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(length - 2))
    return core + secrets.choice("!@#$%*") + secrets.choice(string.digits)


def _get_or_create_org(admin, name: str, contact_email: str) -> str:
    existing = (
        admin.table("organizations").select("id, name").eq("name", name).execute()
    )
    if existing.data:
        org_id = existing.data[0]["id"]
        print(f"• Organisation « {name} » déjà existante → réutilisée ({org_id})")
        return org_id

    org = admin.table("organizations").insert({
        "name": name,
        "email": contact_email,
        "plan": "solo",
        "tasks_limit": settings.PLAN_LIMITS["solo"]["tasks"],
        "country": "CH",
        "language": "fr",
        "currency": "CHF",
        "vat_rate": 8.10,
    }).execute()
    org_id = org.data[0]["id"]
    print(f"• Organisation « {name} » créée ({org_id})")
    return org_id


def _create_user(admin, email: str, org_id: str, role: str, full_name: str) -> dict:
    """Crée le user auth + la ligne users. Idempotent sur l'email."""
    # Déjà présent dans la table users (via auth) ?
    try:
        existing = admin.auth.admin.list_users()
        for u in existing:
            if (getattr(u, "email", "") or "").lower() == email.lower():
                return {"email": email, "status": "exists", "password": None}
    except Exception:
        pass  # on tente la création, qui échouera proprement si doublon

    password = _gen_password()
    try:
        created = admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name},
        })
        user_id = created.user.id
    except Exception as e:
        return {"email": email, "status": f"erreur auth: {e}", "password": None}

    try:
        admin.table("users").insert({
            "id": user_id,
            "organization_id": org_id,
            "role": role,
            "full_name": full_name,
        }).execute()
    except Exception as e:
        return {"email": email, "status": f"erreur users: {e}", "password": None}

    return {"email": email, "status": "créé", "password": password, "role": role}


def main() -> int:
    parser = argparse.ArgumentParser(description="Crée une org + son équipe.")
    parser.add_argument("--org", default="Conti", help="Nom de l'organisation")
    parser.add_argument("--emails", default="", help="Emails séparés par des virgules")
    parser.add_argument("--emails-file", default="", help="Fichier, 1 email par ligne")
    args = parser.parse_args()

    emails: list[str] = []
    if args.emails:
        emails = [e.strip() for e in args.emails.split(",") if e.strip()]
    elif args.emails_file:
        with open(args.emails_file) as f:
            emails = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    if not emails:
        print("Aucun email fourni. Utilisez --emails ou --emails-file.", file=sys.stderr)
        return 1

    admin = get_supabase_admin()
    org_id = _get_or_create_org(admin, args.org, emails[0])

    results = []
    for i, email in enumerate(emails):
        role = "admin" if i == 0 else "member"
        full_name = email.split("@")[0].replace(".", " ").title()
        results.append(_create_user(admin, email, org_id, role, full_name))

    # Récapitulatif
    print("\n" + "=" * 72)
    print(f"ÉQUIPE « {args.org} » — {org_id}")
    print("=" * 72)
    print(f"{'EMAIL':<34}{'RÔLE':<10}{'MOT DE PASSE':<20}STATUT")
    print("-" * 72)
    for r in results:
        pwd = r.get("password") or "—"
        role = r.get("role") or ""
        print(f"{r['email']:<34}{role:<10}{pwd:<20}{r['status']}")
    print("=" * 72)
    print("⚠️  Distribuez ces mots de passe de façon sécurisée puis effacez cette sortie.")
    print("    Chaque ingénieur peut se connecter immédiatement et changer son mot de passe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
