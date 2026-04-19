"""Extraction de consommation énergétique depuis une facture PDF.

Stratégie à 3 niveaux :

1. **PyMuPDF (fitz)** : extraction texte rapide pour PDF texte natifs
   → confidence 0.85 si patterns trouvés
2. **Tesseract OCR** : fallback si PDF est une image scannée
   → confidence 0.65 après OCR
3. **Claude Haiku Vision** : fallback ultime si confidence < 0.80
   → confidence ramenée à celle du LLM (typiquement 0.85-0.95)

L'extraction cherche :
- Valeur consommée (numérique, support apostrophes suisses)
- Unité (m³, litres, kWh, MWh, kg, stères)
- Période (date début + date fin)

Le vecteur énergétique est passé en argument (connu depuis le bâtiment),
ce qui réduit l'ambiguïté.
"""
from __future__ import annotations

import base64
import io
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger(__name__)

CONFIDENCE_OK_THRESHOLD: Final[float] = 0.80
CLAUDE_FALLBACK_MODEL: Final[str] = "claude-haiku-4-5-20251001"
CLAUDE_TIMEOUT_SECONDS: Final[int] = 60

# Patterns par vecteur énergétique - tolère apostrophes suisses + virgule/point
NUMBER_PATTERN: Final[str] = r"([\d]{1,3}(?:[' ]?\d{3})*(?:[.,]\d{1,3})?|\d+(?:[.,]\d{1,3})?)"

PATTERNS_BY_VECTEUR: Final[dict[str, list[tuple[str, str]]]] = {
    "gaz": [
        (rf"(?:consommation|total|volume)[^\d]{{0,40}}{NUMBER_PATTERN}\s*(m\s*[³3])", "m3"),
        (rf"{NUMBER_PATTERN}\s*(m\s*[³3])\s*(?:consomm|factur|total|livr)", "m3"),
        (rf"{NUMBER_PATTERN}\s*(m\s*[³3])", "m3"),
    ],
    "mazout": [
        (rf"{NUMBER_PATTERN}\s*(litres?|l)\s*livr", "litre"),
        (rf"(?:quantit[éeè]|volume|livr|total)[^\d]{{0,40}}{NUMBER_PATTERN}\s*(litres?|l)\b", "litre"),
        (rf"{NUMBER_PATTERN}\s*(litres?|l)\b", "litre"),
    ],
    "pellet": [
        (rf"{NUMBER_PATTERN}\s*(kg|tonnes?|t)\s*(?:granul|pellet)", "kg"),
        (rf"(?:granul|pellet)[^\d]{{0,40}}{NUMBER_PATTERN}\s*(kg|tonnes?)", "kg"),
    ],
    "buche": [
        (rf"{NUMBER_PATTERN}\s*(st[eéè]res?|m3)\s*(?:bois|b[uû]che)", "stere"),
    ],
    "chauffage_distance": [
        (rf"{NUMBER_PATTERN}\s*(kwh|mwh)", "kwh"),
        (rf"(?:consommation|total)[^\d]{{0,40}}{NUMBER_PATTERN}\s*(kwh|mwh)", "kwh"),
    ],
    "electrique": [
        (rf"{NUMBER_PATTERN}\s*(kwh|mwh)", "kwh"),
    ],
    "pac_air_eau": [
        (rf"{NUMBER_PATTERN}\s*(kwh|mwh)", "kwh"),
    ],
    "pac_sol_eau": [
        (rf"{NUMBER_PATTERN}\s*(kwh|mwh)", "kwh"),
    ],
}

# Patterns pour dates
DATE_PATTERN: Final[str] = r"(\d{1,2})[./\- ](\d{1,2})[./\- ](\d{2,4})"
PERIOD_PATTERN: Final[str] = (
    rf"(?:du|p[eé]riode|de)\s+{DATE_PATTERN}\s+(?:au|[àa]|-)\s+{DATE_PATTERN}"
)


@dataclass
class ExtractionResult:
    """Résultat d'extraction depuis une facture PDF."""

    value: float | None
    unit: str | None
    period_start: date | None
    period_end: date | None
    confidence: float
    extraction_method: str
    warnings: list[str] = field(default_factory=list)
    raw_text_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "confidence": round(self.confidence, 3),
            "extraction_method": self.extraction_method,
            "warnings": self.warnings,
        }


class FactureExtractor:
    """Extracteur de consommations depuis factures PDF."""

    def __init__(self, enable_claude_fallback: bool = True) -> None:
        self.enable_claude_fallback = enable_claude_fallback and bool(
            os.environ.get("ANTHROPIC_API_KEY")
        )

    def extract(self, pdf_bytes: bytes, vector: str) -> ExtractionResult:
        """Extrait une consommation + période depuis le PDF.

        Lève ValueError si PDF illisible ou vecteur inconnu.
        """
        if not pdf_bytes:
            raise ValueError("pdf_bytes vide")
        if vector not in PATTERNS_BY_VECTEUR:
            raise ValueError(f"Vecteur non supporté : {vector}")

        # 1. PyMuPDF
        text, method = self._extract_text_fitz(pdf_bytes)
        if text:
            result = self._parse_text(text, vector, method="pymupdf")
            result.raw_text_preview = text[:500]
            if result.confidence >= CONFIDENCE_OK_THRESHOLD:
                return result

            # Si confiance insuffisante, on garde ce résultat comme baseline
            baseline = result
        else:
            baseline = ExtractionResult(
                value=None, unit=None, period_start=None, period_end=None,
                confidence=0.0, extraction_method="pymupdf_empty",
                warnings=["PyMuPDF n'a extrait aucun texte"],
            )

        # 2. Tesseract OCR (si PDF scanné)
        ocr_text = self._extract_text_tesseract(pdf_bytes, baseline.warnings)
        if ocr_text:
            ocr_result = self._parse_text(ocr_text, vector, method="tesseract")
            ocr_result.raw_text_preview = ocr_text[:500]
            ocr_result.confidence = min(ocr_result.confidence, 0.75)  # OCR moins fiable
            if ocr_result.confidence > baseline.confidence:
                baseline = ocr_result

        if baseline.confidence >= CONFIDENCE_OK_THRESHOLD:
            return baseline

        # 3. Claude Haiku Vision (si confiance toujours insuffisante)
        if self.enable_claude_fallback:
            try:
                claude_result = self._extract_via_claude(pdf_bytes, vector, baseline.warnings)
                if claude_result and claude_result.confidence > baseline.confidence:
                    return claude_result
            except Exception as exc:
                baseline.warnings.append(f"Claude Vision fallback échoué : {exc}")

        return baseline

    # ---------- PyMuPDF ----------

    @staticmethod
    def _extract_text_fitz(pdf_bytes: bytes) -> tuple[str, str]:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF non disponible")
            return "", "pymupdf_unavailable"

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = []
            for page in doc:
                pages.append(page.get_text("text"))
            doc.close()
            text = "\n".join(pages).strip()
            return text, "pymupdf"
        except Exception as exc:
            logger.warning("PyMuPDF extraction échec : %s", exc)
            return "", "pymupdf_error"

    # ---------- Tesseract ----------

    @staticmethod
    def _extract_text_tesseract(pdf_bytes: bytes, warnings: list[str]) -> str:
        try:
            import fitz
            import pytesseract
            from PIL import Image
        except ImportError:
            warnings.append("Tesseract/PyMuPDF non disponibles pour OCR")
            return ""

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages_text = []
            for page_num, page in enumerate(doc):
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img, lang="fra+eng", timeout=30)
                pages_text.append(text)
            doc.close()
            return "\n".join(pages_text).strip()
        except Exception as exc:
            warnings.append(f"Tesseract échoué : {exc}")
            return ""

    # ---------- Parsing texte ----------

    def _parse_text(self, text: str, vector: str, method: str) -> ExtractionResult:
        result = ExtractionResult(
            value=None, unit=None, period_start=None, period_end=None,
            confidence=0.0, extraction_method=method,
        )

        lower = text.lower()
        patterns = PATTERNS_BY_VECTEUR.get(vector, [])

        best_value: float | None = None
        best_unit: str | None = None
        best_confidence = 0.0

        for pattern, unit_hint in patterns:
            for match in re.finditer(pattern, lower, re.IGNORECASE):
                num_str = match.group(1)
                value = self._parse_swiss_number(num_str)
                if value is None:
                    continue
                # Plage de sanité selon vecteur
                if not self._is_sane_value(value, vector):
                    continue
                # Confiance selon position dans liste (premier pattern = meilleur)
                pattern_idx = patterns.index((pattern, unit_hint))
                conf = 0.9 - pattern_idx * 0.1
                if conf > best_confidence:
                    best_value = value
                    best_unit = unit_hint
                    best_confidence = conf

        result.value = best_value
        result.unit = best_unit
        result.confidence = best_confidence

        # Période
        period_match = re.search(PERIOD_PATTERN, lower, re.IGNORECASE)
        if period_match:
            try:
                d1 = self._parse_date(period_match.group(1), period_match.group(2), period_match.group(3))
                d2 = self._parse_date(period_match.group(4), period_match.group(5), period_match.group(6))
                if d1 and d2:
                    result.period_start = d1
                    result.period_end = d2
            except ValueError:
                pass

        if best_value is None:
            result.warnings.append(f"Aucune valeur trouvée dans {method} text")
        elif best_confidence < CONFIDENCE_OK_THRESHOLD:
            result.warnings.append(f"Confiance {best_confidence:.2f} < {CONFIDENCE_OK_THRESHOLD}")

        return result

    @staticmethod
    def _parse_swiss_number(s: str) -> float | None:
        """Parse un nombre au format suisse : 1'234.56 / 1 234,56 / 1234.5."""
        s = s.strip().replace("'", "").replace(" ", "")
        # Si virgule + point : le point est le séparateur de milliers (ex : 1.234,56)
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def _is_sane_value(value: float, vector: str) -> bool:
        """Plages de validité par vecteur (évite d'attraper des numéros de client)."""
        if vector == "gaz":
            return 10 <= value <= 10_000_000    # m³
        if vector == "mazout":
            return 50 <= value <= 500_000       # litres
        if vector == "pellet":
            return 10 <= value <= 500_000       # kg
        if vector == "buche":
            return 0.5 <= value <= 1000         # stères
        if vector in ("chauffage_distance", "electrique", "pac_air_eau", "pac_sol_eau"):
            return 100 <= value <= 50_000_000   # kWh
        return 0 < value < 10_000_000

    @staticmethod
    def _parse_date(d: str, m: str, y: str) -> date | None:
        try:
            day, month = int(d), int(m)
            year = int(y)
            if year < 100:
                year += 2000 if year < 70 else 1900
            if 1 <= day <= 31 and 1 <= month <= 12 and 1990 <= year <= 2100:
                return date(year, month, day)
        except (ValueError, TypeError):
            return None
        return None

    # ---------- Claude Vision fallback ----------

    def _extract_via_claude(
        self,
        pdf_bytes: bytes,
        vector: str,
        existing_warnings: list[str],
    ) -> ExtractionResult | None:
        """Fallback via Claude Haiku Vision."""
        try:
            from anthropic import Anthropic
        except ImportError:
            return None

        # Convertir la 1ère page PDF en image JPEG
        image_b64 = self._pdf_first_page_to_base64(pdf_bytes)
        if not image_b64:
            return None

        client = Anthropic(timeout=CLAUDE_TIMEOUT_SECONDS)

        prompt = f"""Tu dois extraire d'une facture énergétique suisse les informations suivantes :

- VALUE : la quantité consommée (nombre décimal)
- UNIT : l'unité exacte ("m3", "litre", "kwh", "mwh", "kg", "stere")
- PERIOD_START : date de début de période (format YYYY-MM-DD) ou null
- PERIOD_END : date de fin de période (format YYYY-MM-DD) ou null

Le vecteur énergétique attendu est : {vector}

Réponds UNIQUEMENT en JSON strict, sans markdown :
{{"value": 1234.5, "unit": "m3", "period_start": "2024-01-01", "period_end": "2024-12-31", "confidence": 0.9}}

Si tu n'as pas trouvé une valeur, mets null. Tes décimaux utilisent le point (.) comme séparateur."""

        start = time.monotonic()
        response = client.messages.create(
            model=CLAUDE_FALLBACK_MODEL,
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        elapsed = time.monotonic() - start

        text = response.content[0].text.strip()
        # Extraction JSON strict
        import json
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start == -1 or brace_end == -1:
            existing_warnings.append("Claude Vision a répondu sans JSON")
            return None

        try:
            data = json.loads(text[brace_start:brace_end + 1])
        except json.JSONDecodeError as exc:
            existing_warnings.append(f"Claude Vision JSON invalide : {exc}")
            return None

        parsed_start = self._parse_iso_date(data.get("period_start"))
        parsed_end = self._parse_iso_date(data.get("period_end"))

        raw_value = data.get("value")
        if raw_value is None:
            return None

        return ExtractionResult(
            value=float(raw_value),
            unit=data.get("unit"),
            period_start=parsed_start,
            period_end=parsed_end,
            confidence=float(data.get("confidence", 0.85)),
            extraction_method="claude_haiku_vision",
            warnings=existing_warnings + [f"Fallback Claude Vision en {elapsed:.1f}s"],
        )

    @staticmethod
    def _pdf_first_page_to_base64(pdf_bytes: bytes) -> str | None:
        try:
            import fitz
        except ImportError:
            return None
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if doc.page_count == 0:
                doc.close()
                return None
            page = doc[0]
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("jpeg")
            doc.close()
            return base64.b64encode(img_bytes).decode("ascii")
        except Exception as exc:
            logger.warning("Conversion PDF→JPEG échec : %s", exc)
            return None

    @staticmethod
    def _parse_iso_date(s: str | None) -> date | None:
        if not s:
            return None
        try:
            return date.fromisoformat(s)
        except (ValueError, TypeError):
            return None
