"""Génération de livrables Word (.docx) éditables à partir du HTML produit par les agents.

Les modules génèrent un corps HTML sémantique (h2/h3, p, ul/ol, table, strong/em)
qui est converti en PDF par WeasyPrint. Ce module convertit ce MÊME HTML en
document Word éditable, pour que l'ingénieur puisse retravailler le livrable.

Aucune dépendance externe supplémentaire : python-docx (déjà présent) + le parseur
HTML de la bibliothèque standard. Le HTML attendu est celui des agents (balises
simples) ; les structures inconnues sont ignorées proprement plutôt que de planter.
"""
from __future__ import annotations

import logging
from html.parser import HTMLParser
from io import BytesIO

from docx import Document
from docx.shared import Pt, RGBColor

logger = logging.getLogger(__name__)

_BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"}
_HEADING_MAP = {"h1": 0, "h2": 1, "h3": 2, "h4": 3, "h5": 4, "h6": 4}
# Balises dont le CONTENU ne doit jamais finir dans le Word (CSS, JS, métadonnées).
# Uniquement des balises à fermeture explicite : les éléments vides (meta, link)
# n'ont pas de </…> et bloqueraient le compteur _skip indéfiniment.
_SKIP_TAGS = {"style", "script", "head", "title"}


class _HtmlToDocx(HTMLParser):
    """Parseur HTML minimal qui pilote un document python-docx."""

    def __init__(self, doc: Document):
        super().__init__(convert_charrefs=True)
        self.doc = doc
        self._bold = 0
        self._italic = 0
        self._para = None  # paragraphe courant
        self._list_stack: list[str] = []  # 'ul' / 'ol'
        # gestion de table
        self._in_table = False
        self._table_rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._cell_buf: list[str] | None = None
        self._is_header_row = False
        self._header_rows: list[bool] = []
        # Contenu non textuel à ignorer (sinon le CSS/JS d'un document complet
        # est recopié tel quel dans le Word).
        self._skip = 0

    # ---- helpers ----
    def _new_para(self, style: str | None = None):
        self._para = self.doc.add_paragraph(style=style) if style else self.doc.add_paragraph()
        return self._para

    def _add_text(self, text: str):
        if not text:
            return
        # Dans une cellule de tableau : on accumule en texte brut
        if self._cell_buf is not None:
            self._cell_buf.append(text)
            return
        if self._para is None:
            self._new_para()
        run = self._para.add_run(text)
        if self._bold:
            run.bold = True
        if self._italic:
            run.italic = True

    # ---- HTMLParser callbacks ----
    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
            return
        if self._skip:
            return
        if tag in ("strong", "b"):
            self._bold += 1
        elif tag in ("em", "i"):
            self._italic += 1
        elif tag in _HEADING_MAP:
            self._para = self.doc.add_heading(level=_HEADING_MAP[tag])
        elif tag == "p":
            self._new_para()
        elif tag == "ul":
            self._list_stack.append("ul")
        elif tag == "ol":
            self._list_stack.append("ol")
        elif tag == "li":
            style = "List Number" if (self._list_stack and self._list_stack[-1] == "ol") else "List Bullet"
            self._new_para(style=style)
        elif tag == "br":
            if self._para is not None:
                self._para.add_run().add_break()
        elif tag == "table":
            self._in_table = True
            self._table_rows = []
            self._header_rows = []
        elif tag == "tr" and self._in_table:
            self._current_row = []
            self._is_header_row = False
        elif tag in ("td", "th") and self._in_table:
            self._cell_buf = []
            if tag == "th":
                self._is_header_row = True

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag in ("strong", "b"):
            self._bold = max(0, self._bold - 1)
        elif tag in ("em", "i"):
            self._italic = max(0, self._italic - 1)
        elif tag in ("p", "li") or tag in _HEADING_MAP:
            self._para = None
        elif tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()
        elif tag in ("td", "th") and self._in_table:
            text = " ".join("".join(self._cell_buf).split()) if self._cell_buf else ""
            if self._current_row is not None:
                self._current_row.append(text)
            self._cell_buf = None
        elif tag == "tr" and self._in_table:
            if self._current_row:
                self._table_rows.append(self._current_row)
                self._header_rows.append(self._is_header_row)
            self._current_row = None
        elif tag == "table" and self._in_table:
            self._flush_table()
            self._in_table = False

    def handle_data(self, data):
        if self._skip:
            return
        if self._cell_buf is not None:
            self._cell_buf.append(data)
            return
        text = data
        if text.strip() == "" and self._para is None:
            return
        # Collapse des espaces multiples hors <pre>
        self._add_text(text if text.strip() else " ")

    def _flush_table(self):
        rows = [r for r in self._table_rows if r]
        if not rows:
            return
        ncols = max(len(r) for r in rows)
        table = self.doc.add_table(rows=0, cols=ncols)
        try:
            table.style = "Light Grid Accent 1"
        except Exception:
            pass
        for i, row in enumerate(rows):
            cells = table.add_row().cells
            for j in range(ncols):
                val = row[j] if j < len(row) else ""
                cells[j].text = val
                # met en gras la ligne d'en-tête
                if self._header_rows[i] if i < len(self._header_rows) else False:
                    for p in cells[j].paragraphs:
                        for run in p.runs:
                            run.bold = True
        self.doc.add_paragraph()


def html_to_docx_bytes(
    body_html: str,
    *,
    title: str = "",
    subtitle: str = "",
    project_info: dict | None = None,
    branding: dict | None = None,
    footer_note: str = "",
) -> bytes:
    """Convertit un corps HTML en document Word éditable et renvoie les octets .docx."""
    doc = Document()

    # Style de base
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    primary = None
    if branding and branding.get("primary_color"):
        try:
            hexv = branding["primary_color"].lstrip("#")
            primary = RGBColor(int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16))
        except Exception:
            primary = None

    # Page de garde simple
    if title:
        h = doc.add_heading(title, level=0)
        if primary:
            for run in h.runs:
                run.font.color.rgb = primary
    if subtitle:
        p = doc.add_paragraph()
        r = p.add_run(subtitle)
        r.italic = True
        r.font.size = Pt(11)

    if project_info:
        for k, v in project_info.items():
            if not v:
                continue
            p = doc.add_paragraph()
            p.add_run(f"{k} : ").bold = True
            p.add_run(str(v))

    if title or subtitle or project_info:
        doc.add_paragraph("―" * 24)

    # Corps
    parser = _HtmlToDocx(doc)
    try:
        parser.feed(body_html or "")
        parser.close()
    except Exception as exc:  # pragma: no cover - robustesse
        logger.warning("Conversion HTML→DOCX partielle : %s", exc)

    if footer_note:
        doc.add_paragraph()
        note = doc.add_paragraph()
        run = note.add_run(footer_note)
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x73, 0x73, 0x73)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def text_to_docx_bytes(text: str, *, title: str = "", footer_note: str = "") -> bytes:
    """Repli : convertit un texte brut (preview) en .docx éditable."""
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    if title:
        doc.add_heading(title, level=0)
    for block in (text or "").split("\n\n"):
        block = block.strip()
        if block:
            doc.add_paragraph(block)
    if footer_note:
        doc.add_paragraph()
        run = doc.add_paragraph().add_run(footer_note)
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x73, 0x73, 0x73)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
