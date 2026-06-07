"""Génération de livrables Word (.docx) éditables et FIDÈLES au PDF.

Les modules produisent un corps HTML sémantique (h1-h6, p, ul/ol, table,
strong/em/a/code, blockquote) qui sert AUSSI à fabriquer le PDF. On convertit ce
même HTML en Word en reproduisant au plus près la mise en page du PDF :
- page de garde (raison sociale, titre à la charte, sous-titre, infos projet) ;
- titres colorés selon la charte client ;
- tableaux avec bordures, en-tête coloré et lignes alternées ;
- listes, gras/italique, liens et code conservés.

Objectif : le Word contient TOUTES les informations du document (chiffres et
textes compris), éditable par l'ingénieur. Aucune dépendance externe en plus.
"""
from __future__ import annotations

import logging
from html.parser import HTMLParser
from io import BytesIO

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

logger = logging.getLogger(__name__)

_HEADING_MAP = {"h1": 1, "h2": 1, "h3": 2, "h4": 3, "h5": 4, "h6": 4}
# Balises dont le CONTENU ne doit jamais finir dans le Word (CSS, JS, métadonnées).
# Uniquement des balises à fermeture explicite : les éléments vides (meta, link)
# bloqueraient sinon le compteur _skip (pas de balise fermante).
_SKIP_TAGS = {"style", "script", "head", "title"}

# Couleurs de repli (charte LESO par défaut) si l'organisation n'en fournit pas.
_DEFAULT_PRIMARY = "1A3A5C"
_DEFAULT_ACCENT = "2E6DA4"
_GREY_TEXT = RGBColor(0x73, 0x73, 0x73)
_HEADER_BORDER = "D0D7DE"
_ZEBRA_FILL = "F4F6F8"


# ---------------------------------------------------------------------------
# Helpers bas niveau (OOXML) pour le style des tableaux
# ---------------------------------------------------------------------------
def _rgb(hexv: str | None, default: RGBColor) -> RGBColor:
    if not hexv:
        return default
    try:
        h = hexv.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return default


def _hex(hexv: str | None, default: str) -> str:
    return (hexv or default).lstrip("#").upper() if hexv else default


def _shade_cell(cell, fill_hex: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def _set_table_borders(table, color_hex: str = _HEADER_BORDER) -> None:
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color_hex)
        borders.append(el)
    tblPr.append(borders)


# ---------------------------------------------------------------------------
# Parseur HTML → docx
# ---------------------------------------------------------------------------
class _HtmlToDocx(HTMLParser):
    """Parseur HTML minimal qui pilote un document python-docx, à la charte."""

    def __init__(self, doc: Document, primary: RGBColor, accent: RGBColor):
        super().__init__(convert_charrefs=True)
        self.doc = doc
        self.primary = primary
        self.accent = accent
        self._bold = 0
        self._italic = 0
        self._mono = 0
        self._para = None
        self._heading_color: RGBColor | None = None
        self._in_quote = False
        self._list_stack: list[str] = []
        # tableau
        self._in_table = False
        self._table_rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._cell_buf: list[str] | None = None
        self._is_header_row = False
        self._header_rows: list[bool] = []
        self._skip = 0

    # ---- helpers ----
    def _new_para(self, style: str | None = None):
        self._para = self.doc.add_paragraph(style=style) if style else self.doc.add_paragraph()
        return self._para

    def _add_text(self, text: str):
        if not text:
            return
        if self._cell_buf is not None:
            self._cell_buf.append(text)
            return
        if self._para is None:
            self._new_para()
        run = self._para.add_run(text)
        if self._bold:
            run.bold = True
        if self._italic or self._in_quote:
            run.italic = True
        if self._mono:
            run.font.name = "Consolas"
        if self._heading_color is not None:
            run.font.color.rgb = self._heading_color

    # ---- callbacks ----
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
        elif tag == "code":
            self._mono += 1
        elif tag in _HEADING_MAP:
            level = _HEADING_MAP[tag]
            self._para = self.doc.add_heading(level=level)
            self._heading_color = self.primary if level <= 2 else self.accent
        elif tag == "p":
            self._new_para()
        elif tag == "blockquote":
            self._in_quote = True
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
        elif tag == "code":
            self._mono = max(0, self._mono - 1)
        elif tag == "blockquote":
            self._in_quote = False
            self._para = None
        elif tag in ("p", "li"):
            self._para = None
        elif tag in _HEADING_MAP:
            self._para = None
            self._heading_color = None
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
        if data.strip() == "" and self._para is None:
            return
        self._add_text(data if data.strip() else " ")

    def _flush_table(self):
        rows = [r for r in self._table_rows if r]
        if not rows:
            return
        ncols = max(len(r) for r in rows)
        # 1re ligne = en-tête si <th> OU par défaut la première ligne.
        header_idx = 0 if (not any(self._header_rows) or self._header_rows[0]) else None

        table = self.doc.add_table(rows=0, cols=ncols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        _set_table_borders(table)

        primary_hex = "%02X%02X%02X" % (self.primary[0], self.primary[1], self.primary[2])
        for i, row in enumerate(rows):
            cells = table.add_row().cells
            is_header = (i == header_idx) or (i < len(self._header_rows) and self._header_rows[i])
            for j in range(ncols):
                val = row[j] if j < len(row) else ""
                cell = cells[j]
                cell.text = ""
                para = cell.paragraphs[0]
                run = para.add_run(val)
                run.font.size = Pt(9.5)
                if is_header:
                    _shade_cell(cell, primary_hex)
                    run.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                elif i % 2 == 0:
                    _shade_cell(cell, _ZEBRA_FILL)
        self.doc.add_paragraph()


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------
def _base_doc() -> Document:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    return doc


def _cover(doc, *, title, subtitle, project_info, primary, accent, org_name):
    if org_name:
        p = doc.add_paragraph()
        r = p.add_run(org_name)
        r.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = accent
    if title:
        h = doc.add_heading(title, level=0)
        for run in h.runs:
            run.font.color.rgb = primary
    if subtitle:
        p = doc.add_paragraph()
        r = p.add_run(subtitle)
        r.italic = True
        r.font.size = Pt(11)
        r.font.color.rgb = _GREY_TEXT

    info = {k: v for k, v in (project_info or {}).items() if v}
    if info:
        table = doc.add_table(rows=0, cols=2)
        table.autofit = True
        _set_table_borders(table)
        primary_hex = "%02X%02X%02X" % (primary[0], primary[1], primary[2])
        for k, v in info.items():
            cells = table.add_row().cells
            cells[0].text = ""
            kr = cells[0].paragraphs[0].add_run(str(k))
            kr.bold = True
            kr.font.size = Pt(9.5)
            kr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            _shade_cell(cells[0], primary_hex)
            cells[1].text = ""
            vr = cells[1].paragraphs[0].add_run(str(v))
            vr.font.size = Pt(9.5)
    if title or subtitle or info:
        doc.add_paragraph()


def html_to_docx_bytes(
    body_html: str,
    *,
    title: str = "",
    subtitle: str = "",
    project_info: dict | None = None,
    branding: dict | None = None,
    footer_note: str = "",
) -> bytes:
    """Convertit un corps HTML en Word fidèle au PDF et renvoie les octets .docx."""
    doc = _base_doc()
    primary = _rgb((branding or {}).get("primary_color"), _rgb(_DEFAULT_PRIMARY, RGBColor(0x1A, 0x3A, 0x5C)))
    accent = _rgb((branding or {}).get("accent_color"), _rgb(_DEFAULT_ACCENT, RGBColor(0x2E, 0x6D, 0xA4)))
    org_name = (branding or {}).get("full_name") or (branding or {}).get("footer_text") or ""

    _cover(doc, title=title, subtitle=subtitle, project_info=project_info,
           primary=primary, accent=accent, org_name=org_name)

    parser = _HtmlToDocx(doc, primary, accent)
    try:
        parser.feed(body_html or "")
        parser.close()
    except Exception as exc:  # pragma: no cover - robustesse
        logger.warning("Conversion HTML→DOCX partielle : %s", exc)

    if footer_note:
        doc.add_paragraph()
        note = doc.add_paragraph().add_run(footer_note)
        note.font.size = Pt(8)
        note.italic = True
        note.font.color.rgb = _GREY_TEXT

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def text_to_docx_bytes(text: str, *, title: str = "", footer_note: str = "") -> bytes:
    """Repli : convertit un texte brut (aperçu) en .docx éditable."""
    doc = _base_doc()
    if title:
        h = doc.add_heading(title, level=0)
        for run in h.runs:
            run.font.color.rgb = _rgb(_DEFAULT_PRIMARY, RGBColor(0x1A, 0x3A, 0x5C))
    for block in (text or "").split("\n\n"):
        block = block.strip()
        if block:
            doc.add_paragraph(block)
    if footer_note:
        doc.add_paragraph()
        run = doc.add_paragraph().add_run(footer_note)
        run.font.size = Pt(8)
        run.italic = True
        run.font.color.rgb = _GREY_TEXT
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
