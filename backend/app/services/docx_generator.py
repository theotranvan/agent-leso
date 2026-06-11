"""Génération de livrables Word (.docx) éditables et FIDÈLES au PDF.

Les modules produisent un corps HTML sémantique (h1-h6, p, ul/ol, table,
strong/em/a/code, blockquote) qui sert AUSSI à fabriquer le PDF. On convertit ce
même HTML en Word en reproduisant au plus près la mise en page du PDF :

- page de GARDE dédiée (raison sociale, grand titre, sous-titre, bloc projet),
  saut de page ensuite ;
- titres dimensionnés à la charte (h1 18pt souligné, h2 13pt, h3 11pt) ;
- tableaux avec bordures fines, en-tête coloré (charte) et lignes alternées ;
- encadré d'avertissement (blockquote) ombré avec liseré ;
- pied de page avec numéro de page + mention de l'organisation ;
- listes, gras/italique, liens et code conservés.

Objectif : le Word contient TOUTES les informations du PDF (chiffres et textes),
au même design, éditable par l'ingénieur. Aucune dépendance externe en plus.
"""
from __future__ import annotations

import logging
from html.parser import HTMLParser
from io import BytesIO

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

logger = logging.getLogger(__name__)

# h1 18pt · h2 13pt · h3 11pt · h4+ 10.5pt (mêmes tailles que le CSS du PDF).
_HEADING_PT = {"h1": 16, "h2": 13, "h3": 11, "h4": 10.5, "h5": 10, "h6": 10}
# Balises dont le CONTENU ne doit jamais finir dans le Word (CSS, JS, métadonnées).
_SKIP_TAGS = {"style", "script", "head", "title"}

# Couleurs de repli (charte LESO par défaut) si l'organisation n'en fournit pas.
_DEFAULT_PRIMARY = "1A3A5C"
_DEFAULT_ACCENT = "2E6DA4"
_GREY_TEXT = RGBColor(0x73, 0x73, 0x73)
_INK = RGBColor(0x17, 0x17, 0x17)
_TABLE_BORDER = "D4D7DE"
_ZEBRA_FILL = "FAFAFA"
_CALLOUT_FILL = "FBF7E9"      # encadré d'avertissement (jaune très pâle)


# ---------------------------------------------------------------------------
# Helpers bas niveau (OOXML)
# ---------------------------------------------------------------------------
def _rgb(hexv: str | None, default: RGBColor) -> RGBColor:
    if not hexv:
        return default
    try:
        h = hexv.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return default


def _hexstr(c: RGBColor) -> str:
    return "%02X%02X%02X" % (c[0], c[1], c[2])


def _shade_cell(cell, fill_hex: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def _set_table_borders(table, color_hex: str = _TABLE_BORDER) -> None:
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


def _para_shading(para, fill_hex: str) -> None:
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    pPr.append(shd)


def _para_border(para, *, edges=("bottom",), color_hex="171717", size="6", space="2") -> None:
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    for edge in edges:
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), size)
        el.set(qn("w:space"), space)
        el.set(qn("w:color"), color_hex)
        pBdr.append(el)
    pPr.append(pBdr)


def _set_default_font(doc: Document, name: str = "Arial") -> None:
    normal = doc.styles["Normal"]
    normal.font.name = name
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = _INK
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rfonts.set(qn(attr), name)


def _add_page_number_footer(doc: Document, org_name: str, accent: RGBColor) -> None:
    """Pied de page : « <org> » à gauche, « Page X / Y » à droite."""
    section = doc.sections[0]
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.text = ""
    # tabulations : centre + droite, alignées sur la largeur utile
    pPr = p._p.get_or_add_pPr()
    tabs = OxmlElement("w:tabs")
    for pos, val in (("9000", "right"),):
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), val)
        tab.set(qn("w:pos"), pos)
        tabs.append(tab)
    pPr.append(tabs)

    left = p.add_run(org_name or "Document généré par LESO")
    left.font.size = Pt(8)
    left.font.color.rgb = _GREY_TEXT
    p.add_run("\t")

    def _field(run_text, instr):
        r = p.add_run()
        r.font.size = Pt(8)
        r.font.color.rgb = _GREY_TEXT
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        instr_el = OxmlElement("w:instrText")
        instr_el.set(qn("xml:space"), "preserve")
        instr_el.text = instr
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        r._r.append(fld_begin)
        r._r.append(instr_el)
        r._r.append(fld_sep)
        r._r.append(fld_end)

    pg = p.add_run("Page ")
    pg.font.size = Pt(8)
    pg.font.color.rgb = _GREY_TEXT
    _field("", "PAGE")
    sep = p.add_run(" / ")
    sep.font.size = Pt(8)
    sep.font.color.rgb = _GREY_TEXT
    _field("", "NUMPAGES")


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
        self._heading_tag: str | None = None
        self._heading_color: RGBColor | None = None
        self._heading_size: float | None = None
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
        if self._bold or self._heading_tag is not None:
            run.bold = True
        if self._italic or self._in_quote:
            run.italic = True
        if self._mono:
            run.font.name = "Consolas"
        if self._heading_size is not None:
            run.font.size = Pt(self._heading_size)
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
        elif tag in _HEADING_PT:
            # Style « Heading N » de Word (mode plan / navigation) + surcharges
            # de charte (taille, couleur, filet) appliquées sur les runs.
            level = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}[tag]
            try:
                self._para = self.doc.add_paragraph(style=f"Heading {level}")
            except Exception:
                self._para = self.doc.add_paragraph()
            self._para.paragraph_format.space_before = Pt(14 if tag in ("h1", "h2") else 8)
            self._para.paragraph_format.space_after = Pt(4)
            self._para.paragraph_format.keep_with_next = True
            self._heading_tag = tag
            self._heading_size = _HEADING_PT[tag]
            self._heading_color = self.primary if tag in ("h1", "h2") else self.accent
            if tag == "h1":   # filet sous le titre, comme le PDF
                _para_border(self._para, edges=("bottom",), color_hex=_hexstr(self.primary), size="8")
        elif tag == "p":
            self._new_para()
        elif tag == "blockquote":
            self._in_quote = True
            self._para = self.doc.add_paragraph()
            self._para.paragraph_format.space_before = Pt(6)
            self._para.paragraph_format.space_after = Pt(6)
            self._para.paragraph_format.left_indent = Cm(0.3)
            self._para.paragraph_format.right_indent = Cm(0.3)
            _para_shading(self._para, _CALLOUT_FILL)
            _para_border(self._para, edges=("left",), color_hex="D9A406", size="18", space="6")
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
        elif tag == "hr":
            sep = self.doc.add_paragraph()
            _para_border(sep, edges=("bottom",), color_hex=_TABLE_BORDER, size="4")
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
        elif tag in _HEADING_PT:
            self._para = None
            self._heading_tag = None
            self._heading_color = None
            self._heading_size = None
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
        header_idx = 0 if (not any(self._header_rows) or self._header_rows[0]) else None

        table = self.doc.add_table(rows=0, cols=ncols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        _set_table_borders(table)
        primary_hex = _hexstr(self.primary)

        for i, row in enumerate(rows):
            cells = table.add_row().cells
            is_header = (i == header_idx) or (i < len(self._header_rows) and self._header_rows[i])
            for j in range(ncols):
                val = row[j] if j < len(row) else ""
                cell = cells[j]
                cell.text = ""
                para = cell.paragraphs[0]
                para.paragraph_format.space_after = Pt(2)
                para.paragraph_format.space_before = Pt(2)
                run = para.add_run(val)
                run.font.size = Pt(9)
                if is_header:
                    _shade_cell(cell, primary_hex)
                    run.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                elif i % 2 == 1:
                    _shade_cell(cell, _ZEBRA_FILL)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------
def _base_doc() -> Document:
    doc = Document()
    _set_default_font(doc, "Arial")
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)
    return doc


def _cover_page(doc, *, title, subtitle, project_info, primary, accent, org_name):
    """Page de garde dédiée, centrée, suivie d'un saut de page (comme le PDF)."""
    def _spacer(pts):
        sp = doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(pts)

    _spacer(90)
    if org_name:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(org_name)
        r.font.size = Pt(11)
        r.font.color.rgb = _GREY_TEXT
    _spacer(36)
    if title:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(title)
        r.bold = True
        r.font.size = Pt(26)
        r.font.color.rgb = primary
    if subtitle:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(subtitle)
        r.font.size = Pt(13)
        r.font.color.rgb = _GREY_TEXT
    _spacer(48)

    info = {k: v for k, v in (project_info or {}).items() if v}
    for k, v in info.items():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        kr = p.add_run(f"{k} : ")
        kr.bold = True
        kr.font.size = Pt(10.5)
        kr.font.color.rgb = _INK
        vr = p.add_run(str(v))
        vr.font.size = Pt(10.5)
        vr.font.color.rgb = _GREY_TEXT

    doc.add_page_break()


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
    primary = _rgb((branding or {}).get("primary_color"), RGBColor(0x1A, 0x3A, 0x5C))
    accent = _rgb((branding or {}).get("accent_color"), RGBColor(0x2E, 0x6D, 0xA4))
    org_name = (branding or {}).get("full_name") or (branding or {}).get("footer_text") \
        or "LESO — Bureau d'Études Techniques"

    _cover_page(doc, title=title, subtitle=subtitle, project_info=project_info,
                primary=primary, accent=accent, org_name=org_name)
    _add_page_number_footer(doc, org_name, accent)

    parser = _HtmlToDocx(doc, primary, accent)
    try:
        parser.feed(body_html or "")
        parser.close()
    except Exception as exc:  # pragma: no cover - robustesse
        logger.warning("Conversion HTML→DOCX partielle : %s", exc)

    if footer_note:
        doc.add_paragraph()
        sep = doc.add_paragraph()
        _para_border(sep, edges=("top",), color_hex=_TABLE_BORDER, size="4")
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
        p = doc.add_paragraph()
        r = p.add_run(title)
        r.bold = True
        r.font.size = Pt(18)
        r.font.color.rgb = RGBColor(0x1A, 0x3A, 0x5C)
        _para_border(p, edges=("bottom",), color_hex="1A3A5C", size="8")
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
