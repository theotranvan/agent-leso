"""Shim V2 → délègue à app.connectors.structural.results_parser."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.connectors.structural.results_parser import SafResultsParser

logger = logging.getLogger(__name__)


def parse_saf_results(saf_xlsx_bytes: bytes, model_data: dict | None = None) -> dict:
    """Parse un SAF xlsx enrichi + effectue le double-check.

    Retourne un dict plat V2-style utilisable par les templates rapport.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(saf_xlsx_bytes)
        tmp_path = Path(tmp.name)

    try:
        parser = SafResultsParser()
        result = parser.parse_and_check(
            saf_input=tmp_path,
            saf_output=tmp_path,
            model_data=model_data or {},
        )
        return result.to_dict()
    finally:
        tmp_path.unlink(missing_ok=True)
