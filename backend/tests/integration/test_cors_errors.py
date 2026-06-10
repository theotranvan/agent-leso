"""Les réponses d'erreur (500) doivent porter les en-têtes CORS.

Régression : un 500 est renvoyé par le ServerErrorMiddleware de Starlette, EN
DEHORS du CORSMiddleware. Sans en-têtes CORS, le navigateur masque l'erreur en
« CORS error » (ex. à l'upload) au lieu d'afficher le vrai 500. On vérifie que
l'origine autorisée est bien reflétée sur une erreur, et qu'une origine non
autorisée ne l'est pas.
"""
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "x")
os.environ.setdefault("OPENAI_API_KEY", "x")
os.environ.setdefault("SUPABASE_URL", "http://x")
os.environ.setdefault("SUPABASE_ANON_KEY", "x")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "x")
os.environ.setdefault("SUPABASE_JWT_SECRET", "x")
os.environ["ALLOWED_ORIGINS"] = "https://leso.ch,https://www.leso.ch"

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


@main.app.get("/api/_boom_test")
async def _boom_test():
    raise RuntimeError("panne simulée (storage/db)")


_client = TestClient(main.app, raise_server_exceptions=False)


def test_500_porte_les_entetes_cors_origine_autorisee():
    r = _client.get("/api/_boom_test", headers={"Origin": "https://leso.ch"})
    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") == "https://leso.ch"
    assert r.headers.get("vary") == "Origin"


def test_500_ne_reflete_pas_une_origine_non_autorisee():
    r = _client.get("/api/_boom_test", headers={"Origin": "https://evil.example"})
    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") is None
