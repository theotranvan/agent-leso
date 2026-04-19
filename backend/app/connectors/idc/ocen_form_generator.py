"""Génération PDF du formulaire IDC OCEN.

Utilise WeasyPrint pour produire un PDF depuis un template HTML/CSS.
Le formulaire est conçu pour être joint à la déclaration IDC annuelle
transmise à l'OCEN.

IMPORTANT : le format exact attendu par l'OCEN peut varier d'une année
à l'autre. Ce générateur produit un PDF **préparatoire** clairement identifié
comme tel. Le document doit toujours être revu par un professionnel avant
soumission officielle.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from app.connectors.idc.idc_calculator import IDCComputationResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OCENFormInput:
    """Entrées pour le formulaire OCEN."""

    egid: str | None
    address: str
    postal_code: str | None
    city: str = "Genève"
    sre_m2: float = 0.0
    heating_vector: str = "gaz"
    building_year: int | None = None
    nb_logements: int | None = None
    regie_name: str | None = None
    regie_email: str | None = None
    regie_phone: str | None = None
    declarant_name: str | None = None


FORM_TEMPLATE_CSS: str = """
@page {
    size: A4;
    margin: 20mm 18mm;
    @bottom-center {
        content: "BET Agent V3 — Document préparatoire IDC — page " counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #737373;
    }
}
* { box-sizing: border-box; }
body {
    font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
    color: #171717;
    line-height: 1.45;
}
h1 { font-size: 18pt; margin: 0 0 6mm; border-bottom: 2px solid #171717; padding-bottom: 2mm; }
h2 { font-size: 13pt; margin: 8mm 0 3mm; color: #1F2937; }
.meta { color: #737373; font-size: 9pt; margin-bottom: 8mm; }
.banner {
    background: #FEF3C7; border: 1px solid #F59E0B; padding: 3mm 4mm;
    margin: 0 0 6mm; font-size: 9pt; color: #92400E;
}
.banner strong { color: #78350F; }
table { width: 100%; border-collapse: collapse; margin: 3mm 0; }
th, td {
    text-align: left; vertical-align: top;
    padding: 2.5mm 3mm; border: 1px solid #E5E5E5; font-size: 9.5pt;
}
th { background: #F5F5F5; font-weight: 600; width: 38%; }
.big-idc {
    text-align: center; padding: 6mm; background: #F9FAFB;
    border: 2px solid #E5E5E5; border-radius: 3mm; margin: 4mm 0;
}
.big-idc .value { font-size: 28pt; font-weight: 700; }
.big-idc .unit { font-size: 11pt; color: #737373; margin-top: 1mm; }
.status { display: inline-block; padding: 1.5mm 4mm; border-radius: 2mm; font-weight: 600; }
.signature-box {
    margin-top: 15mm; border-top: 1px solid #171717; padding-top: 3mm;
    display: flex; justify-content: space-between;
}
.signature-box div { width: 48%; }
.hr { border-top: 1px dashed #A3A3A3; margin: 6mm 0; }
.footer-note { font-size: 8.5pt; color: #737373; margin-top: 6mm; }
"""


class OCENFormGenerator:
    """Génère un PDF préparatoire de déclaration IDC annuelle."""

    def generate(
        self,
        form_input: OCENFormInput,
        idc_result: IDCComputationResult,
    ) -> bytes:
        """Retourne les bytes du PDF."""
        try:
            from weasyprint import HTML, CSS
        except ImportError as exc:
            raise RuntimeError("WeasyPrint non installé") from exc

        html_str = self._render_html(form_input, idc_result)
        buf = BytesIO()
        HTML(string=html_str).write_pdf(
            buf,
            stylesheets=[CSS(string=FORM_TEMPLATE_CSS)],
        )
        pdf_bytes = buf.getvalue()
        logger.info(
            "Formulaire OCEN PDF généré : %.1f KB pour bâtiment EGID %s année %d",
            len(pdf_bytes) / 1024, form_input.egid or "?", idc_result.year,
        )
        return pdf_bytes

    @staticmethod
    def _render_html(form_input: OCENFormInput, idc: IDCComputationResult) -> str:
        status = idc.classification
        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        vectorial_labels = {
            "gaz": "Gaz naturel",
            "mazout": "Mazout",
            "chauffage_distance": "Chauffage à distance (CAD)",
            "pac_air_eau": "Pompe à chaleur air-eau",
            "pac_sol_eau": "Pompe à chaleur sol-eau",
            "pellet": "Granulés bois (pellets)",
            "buche": "Bûches de bois",
            "electrique": "Chauffage électrique direct",
            "solaire_thermique": "Solaire thermique",
        }
        vector_label = vectorial_labels.get(form_input.heating_vector, form_input.heating_vector)

        def fmt_num(n: float, decimals: int = 1) -> str:
            return f"{n:,.{decimals}f}".replace(",", "'")

        html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>Déclaration IDC {idc.year}</title></head>
<body>

<h1>Déclaration annuelle IDC — Canton de Genève</h1>
<div class="meta">Année de mesure : <strong>{idc.year}</strong> &nbsp;|&nbsp; Généré le {generated_at}</div>

<div class="banner">
    <strong>⚠ Document préparatoire</strong> — Ce formulaire a été généré automatiquement
    par BET Agent à partir des factures transmises. Il doit être vérifié et signé par
    un professionnel qualifié avant transmission à l'OCEN.
</div>

<h2>1. Identification du bâtiment</h2>
<table>
    <tr><th>EGID (identifiant fédéral)</th><td>{form_input.egid or '—'}</td></tr>
    <tr><th>Adresse</th><td>{form_input.address}</td></tr>
    <tr><th>Code postal / Localité</th><td>{form_input.postal_code or '—'} {form_input.city}</td></tr>
    <tr><th>Année de construction</th><td>{form_input.building_year or '—'}</td></tr>
    <tr><th>Nombre de logements</th><td>{form_input.nb_logements or '—'}</td></tr>
    <tr><th>Surface de Référence Énergétique (SRE)</th><td>{fmt_num(form_input.sre_m2, 2)} m²</td></tr>
</table>

<h2>2. Système de chauffage</h2>
<table>
    <tr><th>Vecteur énergétique</th><td>{vector_label}</td></tr>
    <tr><th>Consommation totale</th><td>{fmt_num(idc.total_energy_kwh, 0)} kWh</td></tr>
    <tr><th>Nombre de factures agrégées</th><td>{int(idc.details.get('nb_consumptions', 0))}</td></tr>
    <tr><th>DJU station (normal)</th><td>{fmt_num(idc.details.get('dju_normal', 0), 0)}</td></tr>
    <tr><th>DJU année mesurée</th><td>{fmt_num(idc.details.get('dju_year_measured', 0), 0)}</td></tr>
    <tr><th>Facteur de correction climatique</th><td>× {fmt_num(idc.climate_correction_factor, 4)}</td></tr>
</table>

<h2>3. Indice de Dépense de Chaleur</h2>
<div class="big-idc">
    <div class="value" style="color: {status.color};">{fmt_num(idc.idc_normalized_kwh_m2_an, 1)}</div>
    <div class="unit">kWh/m²·an (normalisé climat)</div>
    <div style="margin-top: 3mm; font-size: 9pt; color: #525252;">
        Équivalent MJ/m²·an : {fmt_num(idc.idc_normalized_mj_m2_an, 0)} &nbsp;|&nbsp;
        Brut (sans correction) : {fmt_num(idc.idc_raw_kwh_m2_an, 1)} kWh/m²·an
    </div>
</div>

<table>
    <tr><th>Classification</th>
        <td><span class="status" style="background:{status.color}22; color:{status.color};">
            {status.status.value}</span> — {status.label}</td></tr>
    <tr><th>Action recommandée</th><td>{status.action_required}</td></tr>
</table>

<h2>4. Contacts</h2>
<table>
    <tr><th>Régie / gestionnaire</th><td>{form_input.regie_name or '—'}</td></tr>
    <tr><th>Email</th><td>{form_input.regie_email or '—'}</td></tr>
    <tr><th>Téléphone</th><td>{form_input.regie_phone or '—'}</td></tr>
    <tr><th>Déclarant (BET / ingénieur)</th><td>{form_input.declarant_name or '—'}</td></tr>
</table>

{OCENFormGenerator._warnings_section(idc.warnings)}

<div class="signature-box">
    <div>
        <strong>Signature déclarant</strong><br>
        Nom : ...........................................<br>
        Date : ...........................................<br><br>
        Signature : ___________________________
    </div>
    <div>
        <strong>Réservé OCEN</strong><br>
        Date de réception : .........................<br>
        Visa : ...........................................
    </div>
</div>

<div class="footer-note">
    Référentiel : Loi sur l'énergie du canton de Genève (LEn-GE, L 2 30) et son règlement d'application (REn-GE).
    Pour toute question, consulter le site de l'OCEN : <strong>ge.ch/ocen</strong>.
    Les seuils utilisés dans ce document sont indicatifs et doivent être confirmés auprès de l'OCEN
    pour l'exercice réglementaire {idc.year}.
</div>

</body></html>"""
        return html

    @staticmethod
    def _warnings_section(warnings: list[str]) -> str:
        if not warnings:
            return ""
        items = "".join(f"<li>{w}</li>" for w in warnings)
        return f"""
<h2>Remarques du calcul</h2>
<ul style="font-size: 9pt; color: #737373;">{items}</ul>
"""
