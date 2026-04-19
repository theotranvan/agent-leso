"""Extraction PDF via PyMuPDF + pdfplumber."""
import logging
from io import BytesIO

import fitz
import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> tuple[str, int]:
    """Retourne (texte complet, nb_pages)."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = [p.get_text("text") for p in doc]
        n = len(doc)
        doc.close()
        return "\n\n".join(pages), n
    except Exception as e:
        logger.error(f"extract_text_from_pdf: {e}")
        return "", 0


def extract_tables_from_pdf(pdf_bytes: bytes) -> list[list[list[str]]]:
    """Extrait tous les tableaux (utile pour métrés/DPGF)."""
    tables = []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                for t in page.extract_tables():
                    if t and len(t) > 1:
                        tables.append([[(c or "").strip() for c in row] for row in t])
    except Exception as e:
        logger.error(f"extract_tables: {e}")
    return tables


def is_scanned_pdf(pdf_bytes: bytes) -> bool:
    text, n = extract_text_from_pdf(pdf_bytes)
    return n > 0 and len(text) / n < 50
