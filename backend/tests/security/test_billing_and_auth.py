"""Tests de sécurité — facturation Stripe, webhooks, auth JWT, garde-fous d'entrée.

Couvre :
  - Cycle Stripe : montée/descente de plan met à jour le quota tokens ;
    suspension après 2 paiements échoués ; résiliation désactive l'org.
  - Vérification de signature des webhooks Stripe (valide acceptée / falsifiée
    rejetée) — c'est LE contrôle qui empêche un tiers d'activer un compte.
  - Durcissement JWT : whitelist d'algorithmes (none/HS512 rejetés), signature
    falsifiée et token expiré rejetés, HS256 légitime accepté.
  - Garde-fous d'entrée CCTP : champs libres bornés (anti-explosion de coût).

Aucun appel réseau réel : Supabase et l'email sont mockés ; les signatures
Stripe sont calculées localement avec le secret de test.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt


# ==========================================================================
# Fake Supabase admin — chaînage table/select/insert/update/eq/maybe_single
# ==========================================================================

class _Result:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Query:
    def __init__(self, store: dict, table: str):
        self._store = store
        self._table = table
        self._filters: dict = {}
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

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def maybe_single(self):
        self._single = True
        return self

    def limit(self, n):
        return self

    def order(self, *a, **k):
        return self

    def _match(self, row):
        return all(row.get(k) == v for k, v in self._filters.items())

    def execute(self):
        rows = self._store.setdefault(self._table, [])
        if self._mode == "insert":
            new = dict(self._payload)
            rows.append(new)
            return _Result([new])
        matched = [r for r in rows if self._match(r)]
        if self._mode == "update":
            for r in matched:
                r.update(self._payload)
            return _Result(matched)
        # select
        if self._single:
            return _Result(matched[0] if matched else None)
        return _Result(matched, count=len(matched))


class FakeAdmin:
    def __init__(self, store: dict):
        self._store = store

    def table(self, name: str):
        return _Query(self._store, name)


@pytest.fixture
def fake_store():
    return {
        "organizations": [{
            "id": "org1",
            "email": "client@example.ch",
            "name": "Bureau Test",
            "stripe_customer_id": "cus_1",
            "plan": "pilot",
            "tokens_limit_monthly": 8_000_000,
            "tokens_used_current_month": 1_000_000,
            "tokens_pack_remaining": 0,
            "active": True,
        }],
    }


# ==========================================================================
# 1. CYCLE STRIPE
# ==========================================================================

class TestStripeBillingCycle:
    def test_subscription_update_sets_token_quota(self, fake_store, monkeypatch):
        """Changement de plan → tokens_limit_monthly recalculé (bug corrigé)."""
        from app.services import stripe_service
        monkeypatch.setattr(stripe_service, "get_supabase_admin", lambda: FakeAdmin(fake_store))

        # price_p = plan "pro" (cf. env de test) → QUOTA_PLANS["pro"] = 20M
        stripe_service._handle_subscription_updated({
            "id": "sub_1",
            "metadata": {"organization_id": "org1"},
            "items": {"data": [{"price": {"id": "price_p"}}]},
            "status": "active",
        })
        org = fake_store["organizations"][0]
        assert org["plan"] == "pro"
        assert org["tokens_limit_monthly"] == 20_000_000, "Le quota tokens doit suivre le plan"
        assert org["active"] is True

    def test_subscription_paused_deactivates(self, fake_store, monkeypatch):
        from app.services import stripe_service
        monkeypatch.setattr(stripe_service, "get_supabase_admin", lambda: FakeAdmin(fake_store))
        stripe_service._handle_subscription_updated({
            "id": "sub_1",
            "metadata": {"organization_id": "org1"},
            "items": {"data": [{"price": {"id": "price_p"}}]},
            "status": "past_due",  # ni active ni trialing
        })
        assert fake_store["organizations"][0]["active"] is False

    def test_first_payment_failure_warns_but_keeps_active(self, fake_store, monkeypatch):
        """1er échec : email d'alerte, compte TOUJOURS actif (tolérance)."""
        from app.services import stripe_service
        sent = []
        monkeypatch.setattr(stripe_service, "get_supabase_admin", lambda: FakeAdmin(fake_store))
        monkeypatch.setattr(
            "app.services.email_service.send_alert_email",
            lambda **kw: sent.append(kw),
        )
        stripe_service._handle_payment_failed({"customer": "cus_1", "attempt_count": 1})
        assert fake_store["organizations"][0]["active"] is True
        assert len(sent) == 1, "Un email d'alerte doit partir dès le 1er échec"

    def test_second_payment_failure_suspends(self, fake_store, monkeypatch):
        """2e échec : suspension (bug corrigé — avant, jamais suspendu)."""
        from app.services import stripe_service
        monkeypatch.setattr(stripe_service, "get_supabase_admin", lambda: FakeAdmin(fake_store))
        monkeypatch.setattr(
            "app.services.email_service.send_alert_email", lambda **kw: None,
        )
        stripe_service._handle_payment_failed({"customer": "cus_1", "attempt_count": 2})
        assert fake_store["organizations"][0]["active"] is False

    def test_subscription_deleted_deactivates(self, fake_store, monkeypatch):
        from app.services import stripe_service
        monkeypatch.setattr(stripe_service, "get_supabase_admin", lambda: FakeAdmin(fake_store))
        stripe_service._handle_subscription_deleted({"customer": "cus_1"})
        org = fake_store["organizations"][0]
        assert org["active"] is False
        assert org["stripe_subscription_id"] is None

    def test_payment_failed_unknown_customer_noop(self, fake_store, monkeypatch):
        from app.services import stripe_service
        monkeypatch.setattr(stripe_service, "get_supabase_admin", lambda: FakeAdmin(fake_store))
        # ne doit pas planter ni suspendre une autre org
        stripe_service._handle_payment_failed({"customer": "cus_inconnu", "attempt_count": 5})
        assert fake_store["organizations"][0]["active"] is True


class TestBillingStatusRoute:
    @pytest.mark.asyncio
    async def test_status_reads_token_columns(self, fake_store, monkeypatch):
        """/billing/status renvoie les colonnes tokens (et non tasks_* obsolètes)."""
        from app.middleware import AuthUser
        from app.routes import billing
        monkeypatch.setattr(billing, "get_supabase_admin", lambda: FakeAdmin(fake_store))
        user = AuthUser(id="u1", email="a@b.ch", organization_id="org1",
                        role="admin", access_token="x")
        out = await billing.status(user)
        assert out["plan"] == "pilot"
        assert out["tokens_limit"] == 8_000_000
        assert out["tokens_used"] == 1_000_000
        assert out["quota_pct"] == pytest.approx(12.5, abs=0.1)
        assert "tokens_total_available" in out


# ==========================================================================
# 2. SIGNATURE WEBHOOK STRIPE
# ==========================================================================

def _stripe_signature(payload: bytes, secret: str, t: int | None = None) -> str:
    t = t or int(time.time())
    signed = f"{t}.".encode() + payload
    sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


class TestStripeWebhookSignature:
    def test_valid_signature_accepted(self):
        from app.config import settings
        from app.services import stripe_service
        payload = json.dumps({"id": "evt_1", "type": "ping", "data": {"object": {}}}).encode()
        header = _stripe_signature(payload, settings.STRIPE_WEBHOOK_SECRET)
        event = stripe_service.verify_webhook_signature(payload, header)
        assert event["type"] == "ping"

    def test_tampered_payload_rejected(self):
        from app.config import settings
        from app.services import stripe_service
        payload = json.dumps({"id": "evt_1", "type": "ping"}).encode()
        header = _stripe_signature(payload, settings.STRIPE_WEBHOOK_SECRET)
        tampered = json.dumps({"id": "evt_1", "type": "checkout.session.completed"}).encode()
        with pytest.raises(Exception):
            stripe_service.verify_webhook_signature(tampered, header)

    def test_wrong_secret_rejected(self):
        from app.services import stripe_service
        payload = json.dumps({"id": "evt_1", "type": "ping"}).encode()
        header = _stripe_signature(payload, "whsec_attaquant")
        with pytest.raises(Exception):
            stripe_service.verify_webhook_signature(payload, header)

    def test_stale_timestamp_rejected(self):
        from app.config import settings
        from app.services import stripe_service
        payload = json.dumps({"id": "evt_1", "type": "ping"}).encode()
        old = int(time.time()) - 10_000  # hors tolérance (300s)
        header = _stripe_signature(payload, settings.STRIPE_WEBHOOK_SECRET, t=old)
        with pytest.raises(Exception):
            stripe_service.verify_webhook_signature(payload, header)


# ==========================================================================
# 3. DURCISSEMENT JWT
# ==========================================================================

def _b64url(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()


def _unsigned_token(header: dict, payload: dict, sig: str = "x") -> str:
    return f"{_b64url(header)}.{_b64url(payload)}.{sig}"


class TestJwtHardening:
    def _valid_payload(self, **over):
        p = {
            "sub": "user-1", "email": "a@b.ch", "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        p.update(over)
        return p

    def test_valid_hs256_accepted(self):
        from app.config import settings
        from app.middleware import verify_supabase_jwt
        token = jwt.encode(self._valid_payload(), settings.SUPABASE_JWT_SECRET, algorithm="HS256")
        decoded = verify_supabase_jwt(token)
        assert decoded["sub"] == "user-1"

    def test_alg_none_rejected(self):
        from app.middleware import verify_supabase_jwt
        token = _unsigned_token({"alg": "none", "typ": "JWT"},
                                {"sub": "x", "aud": "authenticated"}, sig="")
        with pytest.raises(HTTPException) as exc:
            verify_supabase_jwt(token)
        assert exc.value.status_code == 401

    def test_unexpected_alg_rejected(self):
        """alg hors whitelist (HS512) refusé AVANT tout décodage / appel JWKS."""
        from app.middleware import verify_supabase_jwt
        token = _unsigned_token({"alg": "HS512", "typ": "JWT"},
                                {"sub": "x", "aud": "authenticated"})
        with pytest.raises(HTTPException) as exc:
            verify_supabase_jwt(token)
        assert exc.value.status_code == 401

    def test_tampered_signature_rejected(self):
        from app.config import settings
        from app.middleware import verify_supabase_jwt
        token = jwt.encode(self._valid_payload(), settings.SUPABASE_JWT_SECRET, algorithm="HS256")
        tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
        with pytest.raises(HTTPException) as exc:
            verify_supabase_jwt(tampered)
        assert exc.value.status_code == 401

    def test_wrong_secret_rejected(self):
        from app.middleware import verify_supabase_jwt
        token = jwt.encode(self._valid_payload(), "secret-de-lattaquant-aaaaaaaaaaaa",
                           algorithm="HS256")
        with pytest.raises(HTTPException) as exc:
            verify_supabase_jwt(token)
        assert exc.value.status_code == 401

    def test_expired_token_rejected(self):
        from app.config import settings
        from app.middleware import verify_supabase_jwt
        token = jwt.encode(
            self._valid_payload(exp=datetime.utcnow() - timedelta(hours=1)),
            settings.SUPABASE_JWT_SECRET, algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            verify_supabase_jwt(token)
        assert exc.value.status_code == 401

    def test_wrong_audience_rejected(self):
        from app.config import settings
        from app.middleware import verify_supabase_jwt
        token = jwt.encode(self._valid_payload(aud="autre-audience"),
                           settings.SUPABASE_JWT_SECRET, algorithm="HS256")
        with pytest.raises(HTTPException) as exc:
            verify_supabase_jwt(token)
        assert exc.value.status_code == 401


# ==========================================================================
# 4. GARDE-FOUS D'ENTRÉE CCTP (anti-explosion de coût / saisie pathologique)
# ==========================================================================

class TestCctpInputCaps:
    def test_normal_input_unchanged(self):
        from app.agent.modules.cctp import _clip, _MAX_ARTICLES_LIBRES
        txt = "Article 1 : robinetterie inox. Article 2 : PAC air-eau COP ≥ 4."
        assert _clip(txt, _MAX_ARTICLES_LIBRES) == txt

    def test_oversized_input_truncated(self):
        from app.agent.modules.cctp import _clip
        big = "x" * 100_000
        out = _clip(big, 50_000)
        assert len(out) <= 50_000 + 20
        assert out.endswith("[…contenu tronqué…]")

    def test_none_and_whitespace_safe(self):
        from app.agent.modules.cctp import _clip
        assert _clip(None, 100) == ""
        assert _clip("   ", 100) == ""
