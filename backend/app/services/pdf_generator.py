"""Génération de PDFs professionnels via WeasyPrint (HTML + CSS → PDF).

Templates Jinja2 avec en-tête, pied de page, table des matières, numérotation.
"""
import logging
from datetime import datetime

from jinja2 import BaseLoader, Environment
from weasyprint import HTML

logger = logging.getLogger(__name__)

_jinja_env = Environment(loader=BaseLoader(), autoescape=True)

# CSS professionnel commun à tous les documents générés
BASE_CSS = """
@page {
    size: A4;
    margin: 2.5cm 2cm 2.5cm 2cm;
    @top-left {
        content: string(doc-title);
        font-size: 9pt;
        color: #737373;
        font-family: 'Helvetica', 'Arial', sans-serif;
    }
    @top-right {
        content: string(project-name);
        font-size: 9pt;
        color: #737373;
        font-family: 'Helvetica', 'Arial', sans-serif;
    }
    @bottom-left {
        content: "Document généré par LESO";
        font-size: 8pt;
        color: #a3a3a3;
        font-family: 'Helvetica', 'Arial', sans-serif;
    }
    @bottom-right {
        content: "Page " counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #a3a3a3;
        font-family: 'Helvetica', 'Arial', sans-serif;
    }
}
@page :first { @top-left { content: none; } @top-right { content: none; } }

body {
    font-family: 'Helvetica', 'Arial', sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #171717;
}

.cover {
    page: cover;
    text-align: center;
    padding-top: 6cm;
    string-set: doc-title content();
    page-break-after: always;
}
.cover h1 { font-size: 28pt; font-weight: 700; margin-bottom: 1cm; color: #0a0a0a; string-set: doc-title content(); }
.cover .subtitle { font-size: 14pt; color: #525252; margin-bottom: 3cm; }
.cover .meta { font-size: 10pt; color: #737373; line-height: 2; }
.cover .meta strong { color: #171717; }

h1 { font-size: 18pt; font-weight: 700; margin-top: 1.2cm; margin-bottom: 0.5cm; color: #0a0a0a; border-bottom: 2px solid #171717; padding-bottom: 0.2cm; string-set: doc-title content(); page-break-after: avoid; }
h2 { font-size: 13pt; font-weight: 600; margin-top: 0.8cm; margin-bottom: 0.3cm; color: #171717; page-break-after: avoid; }
h3 { font-size: 11pt; font-weight: 600; margin-top: 0.5cm; margin-bottom: 0.2cm; color: #262626; page-break-after: avoid; }

p { margin: 0.3cm 0; text-align: justify; }
ul, ol { margin: 0.3cm 0; padding-left: 1cm; }
li { margin: 0.1cm 0; }

/* Les tableaux peuvent se couper entre les pages (un tableau insécable plus
   haut qu'une page provoquait une page blanche + débordement) ; les LIGNES
   restent insécables et l'en-tête se répète sur chaque page. */
table { width: 100%; border-collapse: collapse; margin: 0.5cm 0; font-size: 9pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
thead { display: table-header-group; }
th { background: #f5f5f5; border: 1px solid #d4d4d4; padding: 6px 8px; text-align: left; font-weight: 600; }
td { border: 1px solid #e5e5e5; padding: 6px 8px; vertical-align: top; }
tr:nth-child(even) td { background: #fafafa; }

.toc { page-break-after: always; }
.toc h1 { margin-top: 0; }
.toc-entry { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dotted #d4d4d4; }
.toc-entry .page { color: #737373; }

.visa-block { margin-top: 2cm; padding: 16px; border: 1px solid #d4d4d4; page-break-inside: avoid; }
.visa-block strong { display: block; margin-bottom: 0.5cm; }
.visa-signature { margin-top: 1.5cm; border-top: 1px solid #a3a3a3; padding-top: 0.3cm; width: 7cm; color: #737373; font-size: 9pt; }

.formula { font-family: 'Courier New', monospace; background: #f5f5f5; padding: 8px 12px; margin: 0.3cm 0; border-left: 3px solid #525252; font-size: 9.5pt; }

.alert { padding: 12px 16px; margin: 0.3cm 0; border-left: 3px solid; font-size: 9.5pt; }
.alert-conform { background: #f0fdf4; border-color: #16a34a; color: #14532d; }
.alert-non-conform { background: #fef2f2; border-color: #dc2626; color: #7f1d1d; }
.alert-warning { background: #fffbeb; border-color: #d97706; color: #78350f; }

.footer-note { font-size: 8pt; color: #737373; margin-top: 1cm; }
"""

COVER_TEMPLATE = """
<div class="cover">
    {% if logo_html %}{{ logo_html|safe }}{% endif %}
    <div style="font-size: 10pt; color: #737373; margin-bottom: 2cm;">{{ footer_org|default("LESO — Bureau d'Études Techniques") }}</div>
    <h1>{{ title }}</h1>
    <div class="subtitle">{{ subtitle }}</div>
    <div class="meta">
        <div><strong>Projet :</strong> {{ project_name }}</div>
        {% if project_address %}<div><strong>Adresse :</strong> {{ project_address }}</div>{% endif %}
        {% if lot %}<div><strong>Lot :</strong> {{ lot }}</div>{% endif %}
        {% if author %}<div><strong>Auteur :</strong> {{ author }}</div>{% endif %}
        <div><strong>Date :</strong> {{ date }}</div>
        <div><strong>Référence :</strong> {{ reference }}</div>
    </div>
</div>
"""


def render_pdf_from_html(
    body_html: str,
    title: str,
    subtitle: str = "",
    project_name: str = "",
    project_address: str = "",
    lot: str = "",
    author: str = "",
    reference: str = "",
    extra_css: str = "",
    include_cover: bool = True,
    branding: dict | None = None,
) -> bytes:
    """Rend un PDF à partir d'un corps HTML + métadonnées.

    Si `branding` est fourni (dict de la charte client), applique les couleurs
    primaire/accent, le logo et le pied de page personnalisés.
    """
    date = datetime.now().strftime("%d/%m/%Y")

    # Charte client : surcharge CSS des couleurs + logo
    branding_css = ""
    logo_html = ""
    footer_org = "LESO — Bureau d'Études Techniques"
    if branding:
        primary = branding.get("primary_color", "#0a0a0a")
        accent = branding.get("accent_color", "#171717")
        branding_css = f"""
        .cover h1 {{ color: {primary} !important; }}
        h1 {{ color: {primary} !important; border-bottom-color: {accent} !important; }}
        h2 {{ color: {primary} !important; }}
        h3 {{ color: {accent} !important; }}
        """
        if branding.get("logo_url"):
            logo_html = f'<img src="{branding["logo_url"]}" style="max-height:60px;margin-bottom:1cm;" alt="logo"/>'
        footer_org = branding.get("footer_text") or branding.get("full_name") or footer_org

    cover_html = ""
    if include_cover:
        cover_template = _jinja_env.from_string(COVER_TEMPLATE)
        cover_html = cover_template.render(
            title=title,
            subtitle=subtitle,
            project_name=project_name,
            project_address=project_address,
            lot=lot,
            author=author,
            date=date,
            reference=reference or f"BET-{datetime.now().strftime('%Y%m%d-%H%M')}",
            logo_html=logo_html,
            footer_org=footer_org,
        )

    full_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>{BASE_CSS}{extra_css}{branding_css}</style>
<style>
  body {{ string-set: project-name "{project_name}"; }}
</style>
</head>
<body>
{cover_html}
{body_html}
</body>
</html>"""

    try:
        return HTML(string=full_html).write_pdf()
    except Exception as e:
        logger.error(f"Erreur génération PDF: {e}")
        raise


def markdown_to_html(md: str) -> str:
    """Conversion Markdown → HTML simple (titres, listes, tableaux, paragraphes).

    Suffisant pour les sorties LLM. Pour du markdown complexe, utiliser `markdown` lib.
    """
    lines = md.split("\n")
    html_parts = []
    in_list = False
    in_olist = False
    in_table = False
    in_code = False
    table_rows: list[str] = []
    quote_buf: list[str] = []

    def flush_list():
        nonlocal in_list, in_olist
        if in_list:
            html_parts.append("</ul>")
            in_list = False
        if in_olist:
            html_parts.append("</ol>")
            in_olist = False

    def flush_quote():
        nonlocal quote_buf
        if quote_buf:
            # Le contenu d'une citation peut lui-même être du markdown
            # (listes, gras) → conversion récursive, puis on encadre.
            inner = markdown_to_html("\n".join(quote_buf))
            html_parts.append(f"<blockquote>{inner}</blockquote>")
            quote_buf = []

    def flush_table():
        nonlocal in_table, table_rows
        if in_table and table_rows:
            html_parts.append("<table>")
            # première ligne = header
            header = table_rows[0]
            html_parts.append("<thead><tr>")
            for cell in header:
                html_parts.append(f"<th>{_inline(cell)}</th>")
            html_parts.append("</tr></thead><tbody>")
            for row in table_rows[1:]:
                html_parts.append("<tr>")
                for cell in row:
                    html_parts.append(f"<td>{_inline(cell)}</td>")
                html_parts.append("</tr>")
            html_parts.append("</tbody></table>")
            in_table = False
            table_rows = []

    import re as _re
    _heading_re = _re.compile(r"^(#{1,6})\s+(.*)$")
    _olist_re = _re.compile(r"^\d+[.)]\s+(.*)$")

    for raw in lines:
        line = raw.rstrip()

        if line.startswith("```"):
            flush_quote()
            in_code = not in_code
            continue
        if in_code:
            html_parts.append(f"<div class='formula'>{_escape(line)}</div>")
            continue

        # Citations (blockquote) : on accumule les lignes « > … » consécutives.
        stripped = line.lstrip()
        if stripped == ">" or stripped.startswith("> "):
            flush_list()
            flush_table()
            quote_buf.append(stripped[1:].lstrip() if stripped != ">" else "")
            continue
        else:
            flush_quote()

        # Tableaux markdown
        if "|" in line and line.strip().startswith("|"):
            flush_list()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            # ligne séparateur "|---|---|"
            if all(set(c) <= set("-: ") for c in cells) and cells:
                continue
            table_rows.append(cells)
            in_table = True
            continue
        else:
            flush_table()

        heading = _heading_re.match(line)
        olist = _olist_re.match(line)

        if line.strip() in ("---", "***", "___"):
            flush_list()
            html_parts.append("<hr>")
        elif heading:
            flush_list()
            level = min(len(heading.group(1)), 6)
            html_parts.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif line.startswith("- ") or line.startswith("* "):
            if in_olist:
                html_parts.append("</ol>")
                in_olist = False
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline(line[2:])}</li>")
        elif olist:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            if not in_olist:
                html_parts.append("<ol>")
                in_olist = True
            html_parts.append(f"<li>{_inline(olist.group(1))}</li>")
        elif line.strip():
            flush_list()
            html_parts.append(f"<p>{_inline(line)}</p>")
        else:
            flush_list()

    flush_quote()
    flush_list()
    flush_table()
    return "\n".join(html_parts)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Formatting inline: liens [texte](url), **gras**, *italique*, `code`."""
    import re
    text = _escape(text)

    # Liens markdown [texte](url). Les ancres internes (#...) ne résolvent pas en
    # PDF → on ne garde que le texte ; les liens http(s) deviennent cliquables.
    def _link(m):
        label, url = m.group(1), m.group(2)
        if url.startswith("#"):
            return label
        return f'<a href="{url}">{label}</a>'
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _link, text)

    # `code` inline
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^\*]+?)\*(?!\*)", r"<em>\1</em>", text)
    return text


def render_visa_block(author: str, role: str = "Ingénieur") -> str:
    """Bloc visa ingénieur à insérer en fin de note de calcul."""
    return f"""
<div class="visa-block">
    <strong>Visa et approbation</strong>
    <p>Document vérifié et approuvé par :</p>
    <p>{author or "........................................"} — {role}</p>
    <div class="visa-signature">Signature et date</div>
</div>
"""
