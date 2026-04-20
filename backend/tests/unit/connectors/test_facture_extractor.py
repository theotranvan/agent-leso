"""Tests FactureExtractor - extraction PDF multi-niveaux."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.connectors.idc.facture_extractor import (
    CONFIDENCE_OK_THRESHOLD,
    FactureExtractor,
)


class TestFactureExtractor:
    def test_extract_mazout_from_real_pdf(self, temp_facture_mazout_pdf: Path) -> None:
        extractor = FactureExtractor(enable_claude_fallback=False)
        result = extractor.extract(temp_facture_mazout_pdf.read_bytes(), vector="mazout")
        assert result.value is not None
        assert 5000 <= result.value <= 5500
        assert result.unit == "litre"

    def test_extract_period_dates(self, temp_facture_mazout_pdf: Path) -> None:
        extractor = FactureExtractor(enable_claude_fallback=False)
        result = extractor.extract(temp_facture_mazout_pdf.read_bytes(), vector="mazout")
        if result.period_start and result.period_end:
            assert result.period_start.year == 2023
            assert result.period_end.year == 2024

    def test_empty_pdf_raises(self) -> None:
        extractor = FactureExtractor(enable_claude_fallback=False)
        with pytest.raises(ValueError, match="vide"):
            extractor.extract(b"", vector="mazout")

    def test_unknown_vector_raises(self) -> None:
        extractor = FactureExtractor(enable_claude_fallback=False)
        with pytest.raises(ValueError, match="Vecteur"):
            extractor.extract(b"%PDF-1.4\n", vector="cold_fusion")

    def test_swiss_number_parser(self) -> None:
        assert FactureExtractor._parse_swiss_number("1'234.56") == 1234.56
        assert FactureExtractor._parse_swiss_number("5250") == 5250.0
        assert FactureExtractor._parse_swiss_number("1234,5") == 1234.5
        assert FactureExtractor._parse_swiss_number("1 234,56") == 1234.56

    def test_sanity_range_filters_noise(self) -> None:
        assert FactureExtractor._is_sane_value(5000, "mazout") is True
        assert FactureExtractor._is_sane_value(10, "mazout") is False  # trop peu
        assert FactureExtractor._is_sane_value(1_000_000, "mazout") is False  # trop
        assert FactureExtractor._is_sane_value(10_000, "gaz") is True
        assert FactureExtractor._is_sane_value(1000, "kwh") is False
