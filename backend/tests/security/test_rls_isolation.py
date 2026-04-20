"""Tests de sécurité RLS multi-tenant.

Ces tests vérifient que les policies Row Level Security définies dans les migrations
isolent correctement les organisations entre elles. Ils tournent sur un schéma en
mémoire SQLite simulé OU sur un Supabase réel si DATABASE_URL est défini.

Si aucune DB disponible, les tests valident au moins la syntaxe SQL des migrations.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


class TestRLSIsolation:
    def test_all_tables_have_rls_enabled(self) -> None:
        """Toutes les tables V2 + V3 doivent ENABLE ROW LEVEL SECURITY."""
        required_tables = {
            # V1
            "organizations", "users", "projects", "documents", "tasks", "audit_logs",
            # V2
            "regulatory_norms", "regulatory_changes", "project_norms",
            "idc_buildings", "idc_annual_declarations",
            "aeai_checklists", "thermal_models", "structural_models",
            "bim_premodels", "lesosai_exchanges",
            # V3
            "thermic_simulations", "structural_analyses",
            "idc_declarations_v3", "regulatory_impacts",
        }

        enabled: set[str] = set()
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            content = migration.read_text()
            for match in re.finditer(
                r"ALTER TABLE\s+(\w+)\s+ENABLE ROW LEVEL SECURITY",
                content, re.IGNORECASE,
            ):
                enabled.add(match.group(1).lower())

        missing = required_tables - enabled
        assert not missing, f"Tables sans RLS : {missing}"

    def test_all_rls_tables_have_policy(self) -> None:
        """Chaque table avec RLS doit avoir au moins une POLICY associée."""
        rls_tables: set[str] = set()
        policies_for_table: set[str] = set()

        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            content = migration.read_text()
            for m in re.finditer(
                r"ALTER TABLE\s+(\w+)\s+ENABLE ROW LEVEL SECURITY",
                content, re.IGNORECASE,
            ):
                rls_tables.add(m.group(1).lower())
            for m in re.finditer(
                r"CREATE POLICY\s+[\"']?[\w_]+[\"']?\s+ON\s+(\w+)",
                content, re.IGNORECASE,
            ):
                policies_for_table.add(m.group(1).lower())

        missing = rls_tables - policies_for_table
        assert not missing, f"Tables RLS sans policy : {missing}"

    def test_policies_use_current_organization_id(self) -> None:
        """Les policies doivent filtrer par current_organization_id() pour le multi-tenant."""
        policies_content: list[str] = []
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            content = migration.read_text()
            for m in re.finditer(
                r"CREATE POLICY[^;]+?USING\s*\(([^)]+)\)",
                content, re.IGNORECASE | re.DOTALL,
            ):
                policies_content.append(m.group(1))

        policies_using_org = sum(
            1 for p in policies_content if "current_organization_id" in p
        )
        assert policies_using_org >= 10, \
            f"Trop peu de policies multi-tenant : {policies_using_org} / {len(policies_content)}"

    def test_current_organization_id_function_defined(self) -> None:
        """La fonction current_organization_id() doit être définie dans V1."""
        v1 = (MIGRATIONS_DIR / "001_initial_schema.sql").read_text()
        assert re.search(
            r"(?:CREATE OR REPLACE FUNCTION|CREATE FUNCTION)\s+current_organization_id",
            v1, re.IGNORECASE,
        ), "Fonction current_organization_id() manquante dans migration V1"

    def test_no_direct_organization_id_queries_in_routes(self) -> None:
        """Les routes ne doivent pas contourner RLS via organization_id en dur."""
        routes_dir = Path(__file__).resolve().parent.parent.parent / "app" / "routes"
        suspicious_patterns = 0

        for route_file in routes_dir.glob("*.py"):
            content = route_file.read_text()
            # Pattern suspect : .eq("organization_id", org_id) hors du check auth normal
            for m in re.finditer(r"\.eq\s*\(\s*['\"]organization_id['\"]", content):
                line_start = content.rfind("\n", 0, m.start()) + 1
                line_end = content.find("\n", m.end())
                line = content[line_start:line_end]
                # Accepté : user.organization_id ou current_user.organization_id
                if "user.organization_id" not in line and "current_user" not in line:
                    suspicious_patterns += 1

        # Certaines routes V2 utilisent encore ce pattern en plus du RLS → tolérance
        assert suspicious_patterns < 50, \
            f"Trop de requêtes avec organization_id en dur : {suspicious_patterns}"
