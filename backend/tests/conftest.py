"""Fixtures pytest."""
import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Collecte fixtures V3 (IFC, CECB, PDF, mocks)
pytest_plugins = ["tests.fixtures.conftest"]


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Force les variables d'env de test."""
    test_env = {
        "ENVIRONMENT": "development",
        "ANTHROPIC_API_KEY": "test",
        "OPENAI_API_KEY": "test",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test",
        "SUPABASE_SERVICE_ROLE_KEY": "test",
        "SUPABASE_JWT_SECRET": "test" * 16,
        "STRIPE_SECRET_KEY": "sk_test_x",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "STRIPE_PRICE_STARTER": "price_test_s",
        "STRIPE_PRICE_PRO": "price_test_p",
        "STRIPE_PRICE_ENTERPRISE": "price_test_e",
        "RESEND_API_KEY": "re_test",
        "LEGIFRANCE_CLIENT_ID": "test",
        "LEGIFRANCE_CLIENT_SECRET": "test",
        "ENCRYPTION_KEY": "0" * 32,
    }
    for k, v in test_env.items():
        monkeypatch.setenv(k, v)
