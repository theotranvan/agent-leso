"""Relevé thermique depuis plans 2D (PDF / images) → données Lesosai.

Pour les bureaux d'études qui, en phase 3.3 (autorisation de construire), ne
disposent PAS encore de maquette IFC mais seulement de plans 2D (façades,
étages, toiture, coupes). Ce module lit ces plans avec l'IA vision et extrait
les données du bilan thermique Lesosai :

  - Surface de référence énergétique (SRE)
  - Surface de toiture
  - Surfaces de façades en contact avec l'extérieur, par orientation
  - Surfaces de façades contre terre
  - Surfaces des fenêtres, par orientation
  - Surfaces des planchers (extérieur / terrain / local non chauffé)
  - Longueurs et types de ponts thermiques

Le résultat est un relevé (PDF + Word) + une fiche de saisie Lesosai
pré-remplie. Chaque valeur porte un niveau de confiance : l'ingénieur
thermicien valide et reste responsable du modèle Lesosai final.
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.agent.router import call_llm
from app.database import get_storage, get_supabase_admin
from app.services.pdf_generator import markdown_to_html, render_pdf_from_html

logger = logging.getLogger(__name__)

ORIENTATIONS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
_MAX_PAGES = 12        # garde-fou : plans volumineux
_MAX_EDGE_PX = 2000    # bornage taille image (limites vision + coût)


SYSTEM_PROMPT = """Tu es un thermicien expérimenté d'un bureau d'études de Suisse romande. \
On te donne UNE planche d'un dossier d'architecte (plan d'étage, façade, toiture ou coupe), \
au format image. Ton rôle : faire le RELEVÉ des grandeurs utiles au bilan thermique SIA 380/1 \
(saisie Lesosai), en lisant les cotes, l'échelle et les annotations de surface présentes sur la planche.

RÈGLES STRICTES :
- N'INVENTE JAMAIS une valeur. Si une grandeur n'est pas lisible/déductible sur CETTE planche, mets null.
- Utilise les cotes et l'échelle indiquées. Les surfaces de locaux sont souvent déjà écrites (m²).
- Pour une FAÇADE : déduis l'orientation depuis le titre (ex. « Façade Sud-Ouest » → SO), donne la \
surface brute d'élévation (largeur × hauteur hors toiture) et la surface vitrée totale (somme des fenêtres).
- Pour un PLAN D'ÉTAGE : additionne les surfaces des locaux CHAUFFÉS (séjour, chambres, cuisine, bains, \
circulation interne) pour la contribution SRE ; exclus garages, caves, locaux techniques non chauffés.
- Pour la TOITURE : surface de toiture (emprise ou développé si indiqué).
- Pour une COUPE : repère les ponts thermiques (balcons, dalles sur extérieur, acrotères, refends \
traversants) avec leur longueur si cotée, et les hauteurs d'étage.

Réponds UNIQUEMENT en JSON strict (aucun texte autour) :
{
  "plan_type": "facade | etage | toiture | coupe | sous_sol | situation | autre",
  "orientation": "N|NE|E|SE|S|SO|O|NO|null",
  "echelle": "1:50 | 1:100 | null",
  "sre_contribution_m2": null,
  "surface_toiture_m2": null,
  "surface_facade_brute_m2": null,
  "surface_fenetres_m2": null,
  "surface_facade_contre_terre_m2": null,
  "surface_plancher_ext_terre_m2": null,
  "ponts_thermiques": [ {"type": "...", "longueur_m": null} ],
  "confiance": "haute | moyenne | faible",
  "remarques": "ce qui est lisible / ce qui manque"
}"""


async def execute(task: dict[str, Any]) -> dict[str, Any]:
    """Extrait le relevé thermique depuis des plans 2D et produit le livrable."""
    params = task.get("input_params") or {}
    org_id = task["organization_id"]
    project_id = task.get("project_id")
    project_name = params.get("project_name") or "Projet"
    author = params.get("author", "")
    canton = params.get("canton", "")

    # Documents : liste [{document_id} | {storage_path}] OU un seul document_id.
    docs = params.get("plan_documents") or []
    single = params.get("document_id") or params.get("plan_document_id")
    if single and not docs:
        docs = [{"document_id": single}]
    if not docs:
        raise ValueError("Aucun plan fourni (plan_documents requis).")

    storage = get_storage()
    admin = get_supabase_admin()

    # 1) Lecture vision planche par planche
    per_plan: list[dict[str, Any]] = []
    total_cost = 0.0
    total_tokens = 0
    for d in docs:
        file_bytes, fname, ftype = _load_document(d, org_id, storage, admin)
        if file_bytes is None:
            per_plan.append({"filename": d.get("filename", "?"), "error": "document introuvable"})
            continue

        # Chemin CAO (DXF/DWG) : HYBRIDE. On MESURE la géométrie (SRE étiquetée,
        # gabarit de façade, toiture — précis et vérifiables) ET on LIT le rendu
        # avec l'IA vision pour les grandeurs non déductibles de la seule
        # géométrie (fenêtres par orientation, façades contre terre, planchers
        # par type de contact, ponts thermiques en coupe). On fusionne ensuite.
        low = fname.lower()
        if ftype == "cad" or low.endswith((".dxf", ".dwg")):
            from app.services.cad.dxf_takeoff import (
                dwg_to_dxf_bytes, dxf_to_png_b64, extract_from_dxf,
            )
            dxf_bytes = file_bytes if low.endswith(".dxf") else dwg_to_dxf_bytes(file_bytes)
            geo = extract_from_dxf(dxf_bytes, fname) if dxf_bytes else None
            vis: dict[str, Any] | None = None
            if dxf_bytes:
                img_b64 = dxf_to_png_b64(dxf_bytes)
                if img_b64:
                    vis, usage = await _read_plan(img_b64, fname, task)
                    total_cost += usage.get("cost_eur", 0) or 0
                    total_tokens += usage.get("tokens_used", 0) or 0

            merged = _merge_geo_vision(geo, vis)
            if merged:
                merged["filename"] = fname
                per_plan.append(merged)
            elif low.endswith(".dwg"):
                per_plan.append({
                    "filename": fname,
                    "error": "DWG non converti sur ce serveur — exportez un DXF (1 clic) ou un PDF",
                })
            else:
                per_plan.append({
                    "filename": fname,
                    "error": "DXF illisible — réexportez-le proprement (ou fournissez un PDF)",
                })
            continue

        images = _to_images_b64(file_bytes, ftype)
        if not images:
            per_plan.append({"filename": fname, "error": "rendu image impossible"})
            continue
        # On lit la 1re planche par fichier (un plan = un fichier en général) ;
        # si multipage, on lit chaque page et on garde la plus informative.
        for page_idx, img_b64 in enumerate(images[:_MAX_PAGES]):
            extracted, usage = await _read_plan(img_b64, fname, task)
            extracted["filename"] = fname + (f" (p.{page_idx + 1})" if len(images) > 1 else "")
            per_plan.append(extracted)
            total_cost += usage.get("cost_eur", 0) or 0
            total_tokens += usage.get("tokens_used", 0) or 0

    # 2) Agrégation des grandeurs thermiques
    takeoff = _aggregate(per_plan)

    # 3) Rapport markdown (relevé) + fiche Lesosai
    report_md = _build_report_md(project_name, canton, takeoff, per_plan)
    body_html = markdown_to_html(report_md)

    # 4) PDF à la charte
    pdf_bytes = render_pdf_from_html(
        body_html=body_html,
        title="Relevé thermique — plans 2D",
        subtitle=f"Données pour saisie Lesosai (SIA 380/1){' — ' + canton if canton else ''}",
        project_name=project_name,
        author=author,
        reference=f"RELEVE-THERMO-{datetime.now().strftime('%Y%m%d-%H%M')}",
    )

    filename = f"releve_thermique_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = f"{org_id}/releve_thermique/{task['id']}/{filename}"
    signed_url = None
    try:
        storage.upload(path, pdf_bytes, content_type="application/pdf")
        signed_url = storage.get_signed_url(path, expires_in=604800)
        admin.table("documents").insert({
            "organization_id": org_id,
            "project_id": project_id,
            "filename": filename,
            "file_type": "pdf",
            "storage_path": path,
            "processed": True,
        }).execute()
    except Exception as exc:
        logger.warning("Relevé thermique : archivage indisponible : %s", exc)

    nb_ok = len([p for p in per_plan if not p.get("error")])
    preview = (
        f"Relevé thermique extrait de {nb_ok} planche(s) — "
        f"SRE ≈ {takeoff['sre_m2'] or '?'} m², toiture ≈ {takeoff['surface_toiture_m2'] or '?'} m², "
        f"{len([o for o in takeoff['facades'].values() if o])} façade(s) par orientation, "
        f"{len(takeoff['ponts_thermiques'])} pont(s) thermique(s). À VALIDER par le thermicien."
    )

    return {
        "result_url": signed_url,
        "preview": preview,
        "model": "claude-opus-4-6",
        "tokens_used": total_tokens,
        "cost_eur": round(total_cost, 4),
        "email_bytes": pdf_bytes,
        "email_filename": filename,
        "result_html": body_html,
        "thermal_takeoff": takeoff,
    }


# ---------------------------------------------------------------------------
# Lecture / rendu
# ---------------------------------------------------------------------------
def _load_document(d: dict, org_id: str, storage, admin) -> tuple[bytes | None, str, str]:
    doc_id = d.get("document_id")
    if doc_id:
        row = admin.table("documents").select("*").eq("id", doc_id).eq(
            "organization_id", org_id).maybe_single().execute()
        if not row.data:
            return None, d.get("filename", "?"), "pdf"
        try:
            return storage.download(row.data["storage_path"]), row.data.get("filename", "plan"), row.data.get("file_type", "pdf")
        except Exception:
            return None, row.data.get("filename", "?"), "pdf"
    path = d.get("storage_path")
    if path:
        try:
            return storage.download(path), Path(path).name, ("image" if path.lower().endswith((".png", ".jpg", ".jpeg")) else "pdf")
        except Exception:
            return None, Path(path).name, "pdf"
    return None, "?", "pdf"


def _to_images_b64(file_bytes: bytes, file_type: str) -> list[str]:
    """Rend un PDF (chaque page) ou une image en JPEG base64, taille bornée."""
    # Image directe
    if file_type == "image" or file_bytes[:3] == b"\xff\xd8\xff" or file_bytes[:8].startswith(b"\x89PNG"):
        try:
            from io import BytesIO

            from PIL import Image
            img = Image.open(BytesIO(file_bytes)).convert("RGB")
            img.thumbnail((_MAX_EDGE_PX, _MAX_EDGE_PX))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return [base64.b64encode(buf.getvalue()).decode("ascii")]
        except Exception as exc:
            logger.warning("Image illisible : %s", exc)
            return []
    # PDF → pages
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        out = []
        for page in doc:
            rect = page.rect
            max_pt = max(rect.width, rect.height) or 1
            zoom = min(3.0, _MAX_EDGE_PX / max_pt)  # cap edge à ~2000px
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            out.append(base64.b64encode(pix.tobytes("jpeg")).decode("ascii"))
            if len(out) >= _MAX_PAGES:
                break
        doc.close()
        return out
    except Exception as exc:
        logger.warning("Rendu PDF→image échoué : %s", exc)
        return []


async def _read_plan(img_b64: str, filename: str, task: dict) -> tuple[dict, dict]:
    """Appelle l'IA vision sur une planche et renvoie (données, usage)."""
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
        {"type": "text", "text": f"Planche : « {filename} ». Fais le relevé thermique de CETTE planche selon le format JSON imposé."},
    ]
    try:
        res = await call_llm(
            task_type="releve_thermique_2d",
            system_prompt=SYSTEM_PROMPT,
            user_content=content,
            max_tokens=1500,
            temperature=0.0,
            organization_id=task.get("organization_id"),
            task_id=task.get("id"),
        )
        data = _parse_json(res.get("text", ""))
        return data, res
    except Exception as exc:
        logger.warning("Lecture vision échouée (%s) : %s", filename, exc)
        return {"error": f"lecture échouée: {exc}"}, {}


_NUM_KEYS = (
    "sre_contribution_m2", "surface_toiture_m2", "surface_facade_brute_m2",
    "surface_fenetres_m2", "surface_facade_contre_terre_m2",
    "surface_plancher_ext_terre_m2",
)


def _merge_geo_vision(geo: dict | None, vis: dict | None) -> dict | None:
    """Fusionne mesure géométrique (CAO) et lecture vision d'une même planche.

    La géométrie prime pour ce qu'elle mesure de façon fiable (SRE étiquetée,
    gabarit de façade, toiture) ; la vision comble le reste (fenêtres, façades
    contre terre, planchers par contact, ponts thermiques en coupe).
    """
    geo = None if (not geo or geo.get("error")) else geo
    vis = None if (not vis or vis.get("error")) else vis
    if not geo and not vis:
        return None
    if not vis:
        return dict(geo)
    if not geo:
        return dict(vis)

    out = dict(vis)
    for kk in _NUM_KEYS:
        if geo.get(kk) is not None:           # une mesure géométrique > estimation vision
            out[kk] = geo[kk]
    if geo.get("orientation"):                # orientation depuis le nom de fichier
        out["orientation"] = geo["orientation"]
    out["plan_type"] = geo.get("plan_type") or out.get("plan_type")
    if geo.get("ponts_thermiques"):
        out["ponts_thermiques"] = geo["ponts_thermiques"]
    out["methode"] = "mesure CAO + lecture vision"
    rem = [r for r in (geo.get("remarques"), vis.get("remarques")) if r]
    if rem:
        out["remarques"] = " | ".join(rem)
    return out


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return {"error": "JSON illisible"}
    try:
        return json.loads(text[s:e + 1])
    except json.JSONDecodeError:
        return {"error": "JSON invalide"}


# ---------------------------------------------------------------------------
# Agrégation
# ---------------------------------------------------------------------------
def _num(v) -> float | None:
    try:
        if v is None:
            return None
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _aggregate(per_plan: list[dict]) -> dict[str, Any]:
    sre = 0.0
    sre_seen = False
    toiture = None
    contre_terre = 0.0
    ct_seen = False
    planchers = 0.0
    pl_seen = False
    facades: dict[str, float | None] = {o: None for o in ORIENTATIONS}
    fenetres: dict[str, float | None] = {o: None for o in ORIENTATIONS}
    ponts: list[dict] = []

    for p in per_plan:
        if p.get("error"):
            continue
        c = _num(p.get("sre_contribution_m2"))
        if c is not None:
            sre += c
            sre_seen = True
        t = _num(p.get("surface_toiture_m2"))
        if t is not None:
            toiture = (toiture or 0) + t
        ct = _num(p.get("surface_facade_contre_terre_m2"))
        if ct is not None:
            contre_terre += ct
            ct_seen = True
        pl = _num(p.get("surface_plancher_ext_terre_m2"))
        if pl is not None:
            planchers += pl
            pl_seen = True
        ori = (p.get("orientation") or "").upper().replace("-", "")
        if ori in facades:
            fb = _num(p.get("surface_facade_brute_m2"))
            if fb is not None:
                facades[ori] = (facades[ori] or 0) + fb
            fw = _num(p.get("surface_fenetres_m2"))
            if fw is not None:
                fenetres[ori] = (fenetres[ori] or 0) + fw
        for pt in (p.get("ponts_thermiques") or []):
            if isinstance(pt, dict) and (pt.get("type") or pt.get("longueur_m")):
                ponts.append({"type": pt.get("type") or "à préciser", "longueur_m": _num(pt.get("longueur_m"))})

    return {
        "sre_m2": round(sre, 1) if sre_seen else None,
        "surface_toiture_m2": round(toiture, 1) if toiture is not None else None,
        "surface_facade_contre_terre_m2": round(contre_terre, 1) if ct_seen else None,
        "surface_plancher_ext_terre_m2": round(planchers, 1) if pl_seen else None,
        "facades": facades,
        "fenetres": fenetres,
        "ponts_thermiques": ponts,
    }


# ---------------------------------------------------------------------------
# Rapport markdown
# ---------------------------------------------------------------------------
def _fmt(v, unit="m²"):
    return f"{v:,.1f} {unit}".replace(",", "'") if isinstance(v, (int, float)) else "_à compléter_"


def _sum_orient(d: dict) -> float | None:
    """Somme des valeurs non nulles d'un dict par orientation (None si tout vide)."""
    vals = [v for v in (d or {}).values() if isinstance(v, (int, float))]
    return round(sum(vals), 1) if vals else None


def _build_report_md(project_name: str, canton: str, t: dict, per_plan: list[dict]) -> str:
    md = f"""# Relevé thermique depuis plans 2D

**Projet :** {project_name}{(' · Canton : ' + canton) if canton else ''}
**Planches analysées :** {len([p for p in per_plan if not p.get('error')])}

> ⚠ Relevé établi par lecture des plans (mesure CAO pour les fichiers DXF/DWG, lecture IA vision pour les PDF/images). Valeurs **à vérifier et valider par l'ingénieur thermicien** avant saisie Lesosai. L'ingénieur signataire reste responsable du modèle énergétique.

## 1. Réponse à votre demande — données pour le bilan Lesosai

| # | Donnée demandée | Valeur relevée | Détail |
|---|---|---|---|
| 1 | Surface de référence énergétique (SRE) | {_fmt(t['sre_m2'])} | locaux chauffés |
| 2 | Surface de toiture | {_fmt(t['surface_toiture_m2'])} | — |
| 3 | Surfaces de façades ext. **par orientation** | {_fmt(_sum_orient(t['facades']))} (total) | **voir § 2** |
| 4 | Surfaces de façades **contre terre** | {_fmt(t['surface_facade_contre_terre_m2'])} | sous-sol / coupes |
| 5 | Surfaces des fenêtres **par orientation** | {_fmt(_sum_orient(t['fenetres']))} (total) | **voir § 3** |
| 6 | Surfaces de planchers (ext./terre/local non chauffé) | {_fmt(t['surface_plancher_ext_terre_m2'])} | dalles |
| 7 | Ponts thermiques (longueur + type) | {len(t['ponts_thermiques'])} repéré(s) | **voir § 4** |

_« à compléter » = donnée non lisible sur les planches fournies (à relever sur un plan/coupe complémentaire ou à confirmer par le thermicien)._

## 2. Façades par orientation

| Orientation | Surface façade brute | dont fenêtres | Façade opaque (estimée) |
|---|---|---|---|
"""
    for o in ORIENTATIONS:
        fac = t["facades"].get(o)
        fen = t["fenetres"].get(o)
        if fac is None and fen is None:
            continue
        opaque = None
        if isinstance(fac, (int, float)):
            opaque = fac - (fen or 0)
        md += f"| {o} | {_fmt(fac)} | {_fmt(fen)} | {_fmt(opaque)} |\n"
    if not any(t["facades"].values()):
        md += "| — | _aucune façade lue_ | | |\n"

    md += "\n## 3. Fenêtres par orientation\n\n| Orientation | Surface vitrée |\n|---|---|\n"
    for o in ORIENTATIONS:
        fen = t["fenetres"].get(o)
        if fen is not None:
            md += f"| {o} | {_fmt(fen)} |\n"
    if not any(v is not None for v in t["fenetres"].values()):
        md += "| — | _à compléter_ |\n"

    md += "\n## 4. Ponts thermiques\n\n| Type | Longueur |\n|---|---|\n"
    if t["ponts_thermiques"]:
        for pt in t["ponts_thermiques"]:
            md += f"| {pt['type']} | {_fmt(pt['longueur_m'], 'm')} |\n"
    else:
        md += "| _à relever sur coupes_ | |\n"

    md += "\n## 5. Détail par planche (traçabilité)\n\n| Planche | Type | Orient. | Méthode | Confiance | Remarques |\n|---|---|---|---|---|---|\n"
    for p in per_plan:
        if p.get("error"):
            md += f"| {p.get('filename', '?')} | — | — | — | — | {p['error']} |\n"
        else:
            md += (
                f"| {p.get('filename', '?')} | {p.get('plan_type', '?')} | "
                f"{p.get('orientation') or '—'} | {p.get('methode', 'lecture vision')} | "
                f"{p.get('confiance', '?')} | {(p.get('remarques') or '')[:50]} |\n"
            )

    md += (
        "\n> **Méthode.** Les fichiers **DXF/DWG** sont **mesurés** sur la géométrie vectorielle (valeurs fiables) ; "
        "les **PDF/images** sont **lus** par IA vision (cotes et annotations, à valider). Les valeurs absentes des "
        "plans sont laissées « à compléter ». Prochaine étape : reporter dans Lesosai (ou via la fiche de saisie) "
        "et lancer le bilan SIA 380/1. L'ingénieur thermicien valide et reste responsable."
    )
    return md
