"""OCR Tesseract avec fallback Claude Vision."""
import base64
import logging
from io import BytesIO

import fitz
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def ocr_image(image_bytes: bytes, lang: str = "fra+eng") -> str:
    try:
        img = Image.open(BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        return pytesseract.image_to_string(img, lang=lang)
    except Exception as e:
        logger.error(f"Tesseract: {e}")
        return ""


def ocr_pdf_scanned(pdf_bytes: bytes, lang: str = "fra+eng", dpi: int = 200) -> str:
    parts = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            parts.append(ocr_image(pix.tobytes("png"), lang=lang))
        doc.close()
    except Exception as e:
        logger.error(f"OCR PDF: {e}")
    return "\n\n".join(parts)


async def ocr_fallback_claude(image_bytes: bytes) -> str:
    """Fallback OCR Claude Haiku Vision."""
    from anthropic import AsyncAnthropic
    from app.config import settings
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=4096,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": "Extrais intégralement tout le texte visible, en préservant la mise en forme (tableaux, listes, titres). Retourne uniquement le texte."},
            ]}])
        return resp.content[0].text if resp.content else ""
    except Exception as e:
        logger.error(f"Claude Vision: {e}")
        return ""
