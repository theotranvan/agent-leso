"""Système de templates PDF configurables par charte client.

Promesse pilote Conti : "Templates configurés à la charte de Conti Ingénierie".
Ce module rend cette promesse RÉELLE.

Architecture :
  - Chaque organisation a une `branding_config` (logo, couleurs, signature, footer)
  - Le PDF generator charge cette config et l'applique aux templates HTML/CSS
  - WeasyPrint convertit en PDF avec rendu fidèle

Usage :
    from app.knowledge_base.templates.charter import get_org_branding, render_doc

    branding = get_org_branding(org_id)
    html = render_doc("cctp", content_dict, branding)
    pdf_bytes = weasyprint.HTML(string=html).write_pdf()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ==========================================================================
# BRANDING CONFIG par organisation
# ==========================================================================

@dataclass
class BrandingConfig:
    """Configuration de charte d'une organisation."""

    # Identité
    organization_name: str
    organization_full_name: str = ""  # raison sociale complète
    organization_address: str = ""
    organization_phone: str = ""
    organization_email: str = ""
    organization_website: str = ""

    # Identité visuelle
    logo_url: Optional[str] = None  # URL signée Supabase Storage
    logo_height_px: int = 60
    primary_color: str = "#1B2E4E"  # marine par défaut
    accent_color: str = "#2E75B6"   # bleu BET
    text_color: str = "#222222"
    muted_color: str = "#666666"

    # Typographie
    font_family: str = "Inter, Arial, sans-serif"
    base_font_size_pt: int = 11

    # Signature / pied de page
    signature_block: str = ""  # nom prénom signataire + titre
    footer_text: str = ""       # mentions légales pied de page
    confidentiality: str = "Confidentiel"

    # Variantes par type de document
    document_variants: dict = field(default_factory=dict)


# Configuration par défaut (fallback)
DEFAULT_BRANDING = BrandingConfig(
    organization_name="BET Agent",
    organization_full_name="BET Agent SA",
    primary_color="#1B2E4E",
    accent_color="#2E75B6",
)


# ==========================================================================
# CSS BASE — partagé par tous les templates
# ==========================================================================

def build_base_css(branding: BrandingConfig) -> str:
    """Génère le CSS commun à tous les templates avec la charte."""
    return f"""
@page {{
    size: A4;
    margin: 22mm 18mm 22mm 18mm;

    @top-left {{
        content: element(header);
    }}
    @bottom-right {{
        content: counter(page) " / " counter(pages);
        font-size: 9pt;
        color: {branding.muted_color};
        font-family: {branding.font_family};
    }}
    @bottom-left {{
        content: "{branding.footer_text or branding.organization_name}";
        font-size: 8pt;
        color: {branding.muted_color};
        font-family: {branding.font_family};
    }}
    @bottom-center {{
        content: "{branding.confidentiality}";
        font-size: 8pt;
        color: {branding.muted_color};
        font-family: {branding.font_family};
        font-style: italic;
    }}
}}

* {{
    box-sizing: border-box;
}}

html, body {{
    font-family: {branding.font_family};
    font-size: {branding.base_font_size_pt}pt;
    color: {branding.text_color};
    line-height: 1.5;
    margin: 0;
    padding: 0;
}}

.doc-header {{
    position: running(header);
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid {branding.accent_color};
    padding-bottom: 6px;
    margin-bottom: 8px;
    font-size: 9pt;
    color: {branding.muted_color};
}}

.doc-header .logo {{
    height: {branding.logo_height_px // 2}px;
}}

.doc-header .meta {{
    text-align: right;
    color: {branding.muted_color};
}}

/* Titres */
h1 {{
    font-size: 18pt;
    font-weight: 600;
    color: {branding.primary_color};
    border-bottom: 2px solid {branding.accent_color};
    padding-bottom: 6px;
    margin: 24px 0 12px 0;
    page-break-after: avoid;
}}

h2 {{
    font-size: 13pt;
    font-weight: 600;
    color: {branding.primary_color};
    margin: 18px 0 8px 0;
    page-break-after: avoid;
}}

h3 {{
    font-size: 11.5pt;
    font-weight: 600;
    color: {branding.accent_color};
    margin: 12px 0 6px 0;
    page-break-after: avoid;
}}

p {{
    margin: 4px 0 8px 0;
    text-align: justify;
}}

ul, ol {{
    margin: 4px 0 8px 0;
    padding-left: 22px;
}}

li {{
    margin: 2px 0;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 10pt;
}}

table th {{
    background: #F2F2F2;
    color: {branding.primary_color};
    font-weight: 600;
    text-align: left;
    padding: 8px;
    border: 1px solid #DDDDDD;
}}

table td {{
    padding: 6px 8px;
    border: 1px solid #DDDDDD;
    vertical-align: top;
}}

table tr:nth-child(even) td {{
    background: #FAFAFA;
}}

/* Encarts */
.callout {{
    background: #F2F6FA;
    border-left: 3px solid {branding.accent_color};
    padding: 10px 12px;
    margin: 12px 0;
    font-size: 10pt;
}}

.callout-warning {{
    background: #FFF8E1;
    border-left: 3px solid #C55A11;
    padding: 10px 12px;
    margin: 12px 0;
    font-size: 10pt;
}}

/* Signature */
.signature-block {{
    margin-top: 40px;
    padding-top: 12px;
    border-top: 1px solid {branding.muted_color};
    font-size: 10pt;
}}

.signature-block .signataire {{
    font-weight: 600;
    color: {branding.primary_color};
}}

/* Page de couverture */
.cover {{
    page-break-after: always;
    text-align: center;
    padding-top: 80px;
}}

.cover .logo-cover {{
    height: {branding.logo_height_px}px;
    margin-bottom: 40px;
}}

.cover h1 {{
    font-size: 28pt;
    border: none;
    margin-top: 0;
    color: {branding.primary_color};
}}

.cover .subtitle {{
    font-size: 14pt;
    color: {branding.accent_color};
    margin-top: 8px;
}}

.cover .project-info {{
    margin-top: 60px;
    font-size: 11pt;
    color: {branding.text_color};
    line-height: 1.8;
}}

.cover .project-info strong {{
    color: {branding.primary_color};
}}

/* Saut de page */
.page-break {{
    page-break-after: always;
}}

/* Mention légale finale */
.legal {{
    font-size: 8pt;
    color: {branding.muted_color};
    text-align: center;
    margin-top: 30px;
    font-style: italic;
}}
"""


# ==========================================================================
# HEADER COMMUN
# ==========================================================================

def build_header_html(branding: BrandingConfig, doc_title: str, doc_date: str) -> str:
    """En-tête HTML répété sur chaque page."""
    logo_img = f'<img class="logo" src="{branding.logo_url}" alt="Logo"/>' if branding.logo_url else ''
    return f"""
<div class="doc-header">
    <div>{logo_img} <span>{branding.organization_name}</span></div>
    <div class="meta">
        {doc_title} · {doc_date}
    </div>
</div>
"""


def build_cover_html(
    branding: BrandingConfig,
    doc_title: str,
    doc_subtitle: str,
    project_info: dict,
) -> str:
    """Page de couverture."""
    logo_html = f'<img class="logo-cover" src="{branding.logo_url}" alt="Logo"/>' if branding.logo_url else ''

    project_rows = ""
    for key, value in project_info.items():
        project_rows += f"<div><strong>{key} :</strong> {value}</div>"

    return f"""
<div class="cover">
    {logo_html}
    <h1>{doc_title}</h1>
    <div class="subtitle">{doc_subtitle}</div>
    <div class="project-info">
        {project_rows}
    </div>
</div>
"""


def build_signature_html(branding: BrandingConfig, custom_signataire: Optional[str] = None) -> str:
    """Bloc signature en fin de document."""
    signataire = custom_signataire or branding.signature_block or "Signature et date"
    return f"""
<div class="signature-block">
    <div>{branding.organization_name}</div>
    <div class="signataire">{signataire}</div>
    <div style="margin-top: 30px;">Date et signature :</div>
    <div style="margin-top: 40px; border-bottom: 1px solid #999; width: 250px;"></div>
</div>
"""


# ==========================================================================
# DOCUMENT BUILDER UNIVERSEL
# ==========================================================================

def render_document(
    doc_type: str,
    title: str,
    subtitle: str,
    project_info: dict,
    body_html: str,
    branding: BrandingConfig,
    custom_signataire: Optional[str] = None,
    doc_date: Optional[str] = None,
) -> str:
    """Rend un document HTML complet prêt pour WeasyPrint.

    Args:
        doc_type: "cctp", "rapport_aeai", "dossier_enquete"...
        title: titre principal de la page de couverture
        subtitle: sous-titre
        project_info: dict {label: value} pour la page de couverture
        body_html: contenu HTML du corps du document
        branding: BrandingConfig de l'organisation
        custom_signataire: si différent du signataire par défaut
        doc_date: date formatée (par défaut, date du jour)

    Returns:
        HTML complet à passer à weasyprint.HTML(string=...).write_pdf()
    """
    if not doc_date:
        from datetime import datetime
        doc_date = datetime.now().strftime("%d.%m.%Y")

    css = build_base_css(branding)
    header = build_header_html(branding, title, doc_date)
    cover = build_cover_html(branding, title, subtitle, project_info)
    signature = build_signature_html(branding, custom_signataire)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>{title}</title>
    <style>{css}</style>
</head>
<body>
    {header}
    {cover}
    {body_html}
    {signature}
    <div class="legal">
        Document généré le {doc_date} — {branding.organization_full_name or branding.organization_name}
    </div>
</body>
</html>
"""


# ==========================================================================
# CHARGEMENT DEPUIS BD
# ==========================================================================

async def get_org_branding(organization_id: str) -> BrandingConfig:
    """Charge la config de charte d'une organisation depuis Supabase.

    Si l'organisation n'a pas configuré sa charte, retourne DEFAULT_BRANDING
    en utilisant son nom.
    """
    try:
        from app.database import get_supabase_admin
        admin = get_supabase_admin()
        org = admin.table("organizations").select(
            "name, branding_config, address, phone, email"
        ).eq("id", organization_id).maybe_single().execute()

        if not org.data:
            return DEFAULT_BRANDING

        bc = org.data.get("branding_config") or {}

        return BrandingConfig(
            organization_name=org.data.get("name", "Organisation"),
            organization_full_name=bc.get("full_name", org.data.get("name", "")),
            organization_address=bc.get("address") or org.data.get("address", ""),
            organization_phone=bc.get("phone") or org.data.get("phone", ""),
            organization_email=bc.get("email") or org.data.get("email", ""),
            organization_website=bc.get("website", ""),
            logo_url=bc.get("logo_url"),
            logo_height_px=int(bc.get("logo_height_px", 60)),
            primary_color=bc.get("primary_color", DEFAULT_BRANDING.primary_color),
            accent_color=bc.get("accent_color", DEFAULT_BRANDING.accent_color),
            text_color=bc.get("text_color", DEFAULT_BRANDING.text_color),
            muted_color=bc.get("muted_color", DEFAULT_BRANDING.muted_color),
            font_family=bc.get("font_family", DEFAULT_BRANDING.font_family),
            base_font_size_pt=int(bc.get("base_font_size_pt", 11)),
            signature_block=bc.get("signature_block", ""),
            footer_text=bc.get("footer_text", ""),
            confidentiality=bc.get("confidentiality", "Confidentiel"),
        )
    except Exception:
        return DEFAULT_BRANDING


def update_org_branding(
    organization_id: str,
    branding_dict: dict,
) -> dict:
    """Met à jour la config de charte d'une organisation."""
    from app.database import get_supabase_admin
    admin = get_supabase_admin()
    result = admin.table("organizations").update({
        "branding_config": branding_dict,
    }).eq("id", organization_id).execute()
    return result.data[0] if result.data else {}
