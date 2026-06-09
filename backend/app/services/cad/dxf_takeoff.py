"""Relevé thermique géométrique depuis un fichier CAO (DXF, ou DWG converti).

Contrairement à la lecture vision d'un PDF aplati (estimation à l'échelle), on
lit ici la GÉOMÉTRIE VECTORIELLE : on MESURE les surfaces et longueurs au lieu de
les estimer. Cible : exports DXF d'ArchiCAD / AutoCAD / Vectorworks (un clic),
ou DWG si un convertisseur dwg2dxf est disponible.

Données extraites selon le type de planche (déduit du nom de fichier) :
  - façade (par orientation) : gabarit brut + surface vitrée (blocs fenêtres) ;
  - toiture                  : surface (plus grande polyligne fermée) ;
  - étage / sous-sol         : SRE (zones chauffées) + surfaces de dalles.

Tout ce qui n'est pas mesurable est laissé à None (jamais inventé). Le résultat
a la MÊME forme que la lecture vision → il s'agrège dans le même pipeline.
"""
from __future__ import annotations

import logging
import re
from io import BytesIO

logger = logging.getLogger(__name__)

# Orientation depuis le nom de fichier (façades).
_ORIENTATIONS = {
    "nord-ouest": "NO", "nord ouest": "NO", "nordwest": "NO",
    "nord-est": "NE", "nord est": "NE", "nordost": "NE",
    "sud-ouest": "SO", "sud ouest": "SO", "südwest": "SO", "sudwest": "SO",
    "sud-est": "SE", "sud est": "SE", "südost": "SE", "sudost": "SE",
    "nord": "N", "sud": "S", "est": "E", "ouest": "O", "west": "O", "ost": "E",
}

# Mots-clés de calques (ArchiCAD/Swiss numérotés ou nommés).
_LYR_PORTEUR = re.compile(r"porteur|mur|wall|101|102|façade|facade|revêtement|revetement|116", re.I)
_LYR_TOITURE = re.compile(r"toiture|roof|charpente|111|dach", re.I)
_LYR_DALLE = re.compile(r"dalle|plancher|radier|slab|floor|109|113", re.I)
_LYR_ZONE = re.compile(r"zone|611|local|locaux|pièce|piece|raum", re.I)
_LYR_FENETRE = re.compile(r"fen[êe]tre|window|menuiserie|baie|201|211|fenster", re.I)
_LYR_SKIP = re.compile(r"cotation|cote|axe|texte|haie|terrain|parcelle|cartouche|logo|mobilier|amén|niveau|601|602|603|501|815|404", re.I)

# Locaux NON chauffés (exclus de la SRE).
_NON_CHAUFFE = re.compile(r"garage|cave|abri|parking|technique|local technique|buanderie|réduit|reduit|cage|circulation ext|balcon|terrasse|loggia|gaine", re.I)


def detect_plan_type(filename: str) -> tuple[str, str | None]:
    """(plan_type, orientation) déduits du nom de fichier."""
    f = (filename or "").lower()
    orient = None
    for k, v in _ORIENTATIONS.items():
        if k in f:
            orient = v
            break
    if "façade" in f or "facade" in f or "elevation" in f or "élévation" in f:
        return "facade", orient
    if "toiture" in f or "toit" in f or "roof" in f or "dach" in f:
        return "toiture", None
    if "coupe" in f or "section" in f or "schnitt" in f:
        return "coupe", None
    if "sous-sol" in f or "sous sol" in f or "ssol" in f or "cave" in f or "untergeschoss" in f:
        return "sous_sol", None
    if "rez" in f or "étage" in f or "etage" in f or "attique" in f or "plan" in f or "niveau" in f or "geschoss" in f:
        return "etage", None
    return "autre", orient


# ---------------------------------------------------------------------------
# Lecture DXF
# ---------------------------------------------------------------------------
def _unit_to_m(doc) -> float:
    """Facteur pour convertir les unités du dessin en mètres."""
    code = 0
    try:
        code = int(doc.header.get("$INSUNITS", 0))
    except Exception:
        code = 0
    # INSUNITS : 1=in,2=ft,4=mm,5=cm,6=m,8=µin,9=mil
    return {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0}.get(code, 0.0)  # 0 => inconnu


def _layer_of(e) -> str:
    try:
        return e.dxf.layer or ""
    except Exception:
        return ""


def _poly_area_m2(e, k: float) -> float:
    """Aire d'une LWPOLYLINE/POLYLINE fermée (shoelace), en m²."""
    try:
        pts = [(p[0], p[1]) for p in e.get_points("xy")]
    except Exception:
        try:
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        except Exception:
            return 0.0
    if len(pts) < 3:
        return 0.0
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2 * (k * k)


def _mtext_plain(e) -> str:
    try:
        if e.dxftype() == "MTEXT":
            return e.plain_text()
        return e.dxf.text or ""
    except Exception:
        return ""


def extract_from_dxf(dxf_bytes: bytes, filename: str) -> dict | None:
    """Mesure géométrique d'une planche DXF. Renvoie un dict (forme vision) ou None."""
    try:
        from ezdxf import recover
        doc, auditor = recover.read(BytesIO(dxf_bytes))
    except Exception as exc:
        logger.warning("DXF illisible (%s) : %s", filename, exc)
        return None

    try:
        msp = doc.modelspace()
    except Exception:
        return None

    plan_type, orientation = detect_plan_type(filename)
    k = _unit_to_m(doc)

    # Détermination de l'unité si inconnue : on devine depuis l'étendue.
    xs: list[float] = []
    ys: list[float] = []
    roof_area = 0.0
    slab_area = 0.0
    sre = 0.0
    sre_seen = False
    window_count = 0
    window_area = 0.0
    notes = []

    for e in msp:
        lyr = _layer_of(e)
        if _LYR_SKIP.search(lyr):
            continue
        dt = e.dxftype()

        # Bornes (gabarit) sur calques porteurs/façade
        if _LYR_PORTEUR.search(lyr) or _LYR_TOITURE.search(lyr) or _LYR_DALLE.search(lyr):
            try:
                if dt in ("LWPOLYLINE", "POLYLINE"):
                    for p in e.get_points("xy"):
                        xs.append(p[0])
                        ys.append(p[1])
                elif dt == "LINE":
                    xs += [e.dxf.start.x, e.dxf.end.x]
                    ys += [e.dxf.start.y, e.dxf.end.y]
            except Exception:
                pass

        # Toiture : plus grande polyligne fermée sur calque toiture
        if _LYR_TOITURE.search(lyr) and dt in ("LWPOLYLINE", "POLYLINE"):
            if getattr(e, "closed", False) or getattr(getattr(e, "dxf", None), "flags", 0):
                roof_area = max(roof_area, _poly_area_m2(e, k or 0.001))

        # Dalles : somme des polylignes fermées sur calque dalle
        if _LYR_DALLE.search(lyr) and dt in ("LWPOLYLINE", "POLYLINE") and getattr(e, "closed", False):
            slab_area += _poly_area_m2(e, k or 0.001)

        # Fenêtres : blocs (INSERT) sur calque/nom fenêtre
        if dt == "INSERT":
            name = ""
            try:
                name = e.dxf.name or ""
            except Exception:
                name = ""
            if _LYR_FENETRE.search(lyr) or _LYR_FENETRE.search(name):
                window_count += 1
                # surface du bloc via sa bbox si dispo
                try:
                    from ezdxf.bbox import extents
                    bb = extents([e])
                    if bb.has_data:
                        w = (bb.extmax.x - bb.extmin.x) * (k or 0.001)
                        h = (bb.extmax.y - bb.extmin.y) * (k or 0.001)
                        if 0.1 < w < 6 and 0.1 < h < 6:
                            window_area += w * h
                except Exception:
                    pass

        # Zones → SRE : texte de surface sur calque zone
        if dt in ("TEXT", "MTEXT") and _LYR_ZONE.search(lyr):
            t = _mtext_plain(e)
            m = re.search(r"(\d{1,4}[.,]\d{1,2})\s*m[²2]", t)
            if m and not _NON_CHAUFFE.search(t):
                try:
                    sre += float(m.group(1).replace(",", "."))
                    sre_seen = True
                except ValueError:
                    pass

    # Si unité inconnue, devine (mm si étendue énorme)
    if not k and xs:
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        k = 0.001 if span > 2000 else 1.0
        notes.append("unité non déclarée — supposée " + ("mm" if k == 0.001 else "m"))

    out: dict = {
        "plan_type": plan_type,
        "orientation": orientation,
        "methode": "mesure CAO (DXF)",
        "confiance": "haute",
        "remarques": "; ".join(notes) or "géométrie vectorielle mesurée",
        "sre_contribution_m2": None,
        "surface_toiture_m2": None,
        "surface_facade_brute_m2": None,
        "surface_fenetres_m2": None,
        "surface_facade_contre_terre_m2": None,
        "surface_plancher_ext_terre_m2": None,
        "ponts_thermiques": [],
    }

    if plan_type == "facade" and xs:
        w = (max(xs) - min(xs)) * k
        h = (max(ys) - min(ys)) * k
        if 1 < w < 200 and 1 < h < 100:
            out["surface_facade_brute_m2"] = round(w * h, 1)
        if window_area > 0:
            out["surface_fenetres_m2"] = round(window_area, 1)
        elif window_count:
            out["remarques"] += f" — {window_count} fenêtre(s) détectée(s), surface à confirmer"
    if plan_type == "toiture" and roof_area > 0:
        out["surface_toiture_m2"] = round(roof_area, 1)
    if plan_type in ("etage", "sous_sol"):
        if sre_seen:
            out["sre_contribution_m2"] = round(sre, 1)
        if slab_area > 0 and plan_type == "sous_sol":
            out["surface_plancher_ext_terre_m2"] = round(slab_area, 1)
    # Fenêtres détectées sur un plan non-façade : on les remonte aussi si orientées
    if plan_type != "facade" and window_area > 0 and orientation:
        out["surface_fenetres_m2"] = round(window_area, 1)

    # Normalise les numériques (évite que des float numpy fuient en JSON/DB).
    for kk in ("sre_contribution_m2", "surface_toiture_m2", "surface_facade_brute_m2",
               "surface_fenetres_m2", "surface_facade_contre_terre_m2", "surface_plancher_ext_terre_m2"):
        if out[kk] is not None:
            out[kk] = float(out[kk])
    return out


def dwg_to_dxf_bytes(dwg_bytes: bytes) -> bytes | None:
    """Convertit un DWG en DXF si un binaire dwg2dxf est disponible (config env)."""
    import os
    import subprocess
    import tempfile
    conv = os.environ.get("LIBREDWG_DWG2DXF") or _which("dwg2dxf")
    if not conv:
        return None
    try:
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.dwg")
            dst = os.path.join(d, "out.dxf")
            with open(src, "wb") as f:
                f.write(dwg_bytes)
            subprocess.run([conv, "-y", "-o", dst, src], check=True,
                           capture_output=True, timeout=120)
            if os.path.exists(dst):
                with open(dst, "rb") as f:
                    return f.read()
    except Exception as exc:
        logger.warning("Conversion DWG→DXF échouée : %s", exc)
    return None


def _which(name: str) -> str | None:
    import shutil
    return shutil.which(name)
