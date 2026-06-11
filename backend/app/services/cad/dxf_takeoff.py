"""Relevé thermique géométrique depuis un fichier CAO (DXF, ou DWG converti).

Contrairement à la lecture vision d'un PDF aplati (estimation à l'échelle), on
lit ici la GÉOMÉTRIE VECTORIELLE : on MESURE les surfaces et longueurs au lieu de
les estimer. Cible : exports DXF d'ArchiCAD / AutoCAD / Vectorworks (un clic),
ou DWG si un convertisseur dwg2dxf est disponible.

Données extraites selon le type de planche (déduit du nom de fichier) :
  - façade (par orientation) : gabarit brut, baies (fenêtres/portes-fenêtres)
    mesurées sur l'élévation, partie contre terre visible (ligne de terrain) ;
  - toiture                  : surface + périmètre (acrotère) ;
  - étage / sous-sol         : SRE (étiquettes architecte, sinon tampons de
    zone ArchiCAD), planchers, périmètre d'étage (jonctions dalle-façade) ;
  - coupe                    : profondeur enterrée (isolation périphérique).

Deux niveaux de lecture du DWG :
  1. conversion MINIMALE (HEADER+ENTITIES) — robuste, calques préservés ;
  2. conversion COMPLÈTE réparée — LibreDWG sérialise mal certaines valeurs
     (retours-ligne bruts dans les MTEXT, entrées de table sans nom) ; on
     répare le texte DXF puis on lit aussi les BLOCS (exports ArchiCAD : tout
     le dessin vit dans des blocs définis en coordonnées monde) et les
     entités orphelines (tampons de zone avec les surfaces des pièces).

Tout ce qui n'est pas mesurable est laissé à None (jamais inventé). Le résultat
a la MÊME forme que la lecture vision → il s'agrège dans le même pipeline.
"""
from __future__ import annotations

import base64
import logging
import math
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
# Surface de façade visible (revêtement / élévation) — calque dédié, plus précis
# que l'enveloppe des porteurs pour mesurer le gabarit d'une façade.
_LYR_FACADE_SURF = re.compile(r"116|revêtement|revetement|élévation|elevation", re.I)
# Calques structurels servant à CADRER le rendu (le bâti, pas le contexte).
_LYR_FRAME = re.compile(
    r"101|102|103|104|porteur|mur|wall|116|revêtement|revetement|109|113|dalle|"
    r"plancher|radier|111|charpente|toiture|roof|611|zone",
    re.I,
)
_LYR_TOITURE = re.compile(r"toiture|roof|charpente|111|dach", re.I)
_LYR_DALLE = re.compile(r"dalle|plancher|radier|slab|floor|109|113", re.I)
_LYR_ZONE = re.compile(r"zone|611|local|locaux|pièce|piece|raum", re.I)
_LYR_FENETRE = re.compile(r"fen[êe]tre|window|menuiserie|baie|201|211|fenster", re.I)
_LYR_TERRAIN = re.compile(r"401|terrain", re.I)
_LYR_ISOL_PERIPH = re.compile(r"104|isolation p[ée]riph", re.I)
# Bruit à exclure : végétation (haies, couronnes, troncs), parcelles, mobilier,
# aménagements extérieurs, cotation/axes/niveaux, escaliers, garde-corps,
# bâtiments hors projet / démolis, terrassement, cartouche.
_LYR_SKIP = re.compile(
    r"cotation|cote|axe|texte|visualisation|haie|nh_|couronne|tronc|arbre|terrain|"
    r"parcelle|numero|cartouche|logo|mobilier|agencement|amén|amen|niveau|escalier|"
    r"garde|démoli|demoli|hors projet|terrassement|601|602|603|501|815|404|402|105|108|003",
    re.I,
)
# Calques exclus de la détection de baies en élévation (revêtement, charpente).
_LYR_PAS_BAIE = re.compile(r"116|revêtement|revetement|111|charpente|toiture|dalle|109|113", re.I)

# Locaux NON chauffés (exclus de la SRE).
_NON_CHAUFFE = re.compile(
    r"garage|cave|abri|parking|technique|local technique|buanderie|réduit|reduit|cage|"
    r"circulation ext|balcon|terrasse|loggia|gaine|couvert|voiture|vélo|velo|carport|"
    r"pergola|jardin|pluie|combl|non chauff",
    re.I,
)

# Noms de pièces chauffées (tampons de zone ArchiCAD).
_PIECE_CHAUFFEE = re.compile(
    r"chambre|séjour|sejour|salon|cuisine|salle|sdb|sdd|wc|bain|douche|bureau|"
    r"entrée|entree|couloir|hall|dressing|mezzanine|réduit chauffé",
    re.I,
)


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
# Helpers géométriques
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


def _pts_of(e) -> list[tuple[float, float]]:
    """Sommets 2D d'une entité (polylignes, lignes, contours de hachures)."""
    try:
        dt = e.dxftype()
        if dt in ("LWPOLYLINE", "POLYLINE"):
            return [(p[0], p[1]) for p in e.get_points("xy")]
        if dt == "LINE":
            return [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
        if dt == "HATCH":
            out = []
            for path in e.paths:
                for v in getattr(path, "vertices", []) or []:
                    out.append((v[0], v[1]))
            return out
    except Exception:
        pass
    return []


def _poly_area_m2(e, k: float) -> float:
    """Aire d'une LWPOLYLINE/POLYLINE fermée (shoelace), en m²."""
    pts = _pts_of(e)
    if len(pts) < 3:
        return 0.0
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2 * (k * k)


def _poly_perimeter_m(e, k: float) -> float:
    """Périmètre d'une polyligne fermée, en m."""
    pts = _pts_of(e)
    if len(pts) < 3:
        return 0.0
    return sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))) * k


def _bbox_of(e):
    try:
        from ezdxf.bbox import extents
        bb = extents([e])
        if bb.has_data:
            return bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y
    except Exception:
        pass
    return None


def _mtext_plain(e) -> str:
    try:
        if e.dxftype() == "MTEXT":
            return e.plain_text()
        return e.dxf.text or ""
    except Exception:
        return ""


_AIRE_RE = re.compile(r"(\d{1,4}[.,]\d{1,2})\s*m\s*[²2]")


# ---------------------------------------------------------------------------
# Mesures spécialisées (élévations)
# ---------------------------------------------------------------------------
def _baies_elevation(msp, k: float, gab: tuple[float, float, float, float]) -> tuple[float, int]:
    """Surface des baies (fenêtres + portes-fenêtres) MESURÉE sur une élévation.

    Les menuiseries sont dessinées en polylignes fermées aux dimensions réelles
    (ex. 1.60×1.40 m). On retient les rectangles « taille de baie » situés dans
    le gabarit de la façade, puis on dédoublonne les cadres imbriqués
    (cadre/vantail/vitrage) en gardant le contour extérieur.
    Renvoie (surface totale m², nombre de baies)."""
    x0, y0, x1, y1 = gab
    cands: list[tuple[float, float, float, float, float]] = []
    for e in msp:
        if e.dxftype() not in ("LWPOLYLINE", "POLYLINE") or not getattr(e, "closed", False):
            continue
        lyr = _layer_of(e)
        if _LYR_SKIP.search(lyr) or _LYR_PAS_BAIE.search(lyr):
            continue
        bb = _bbox_of(e)
        if not bb:
            continue
        bx0, by0, bx1, by1 = bb
        w = (bx1 - bx0) * k
        h = (by1 - by0) * k
        if not (0.4 <= w <= 5.0 and 0.4 <= h <= 3.5 and w * h >= 0.3):
            continue
        # dans le gabarit de la façade (tolérance 20 cm)
        tol = 0.2 / k
        if bx0 < x0 - tol or bx1 > x1 + tol or by0 < y0 - tol or by1 > y1 + tol:
            continue
        cands.append((bx0, by0, bx1, by1, w * h))

    # Dédoublonnage : contours imbriqués (on garde l'extérieur) et quasi-doublons.
    keep: list[tuple[float, float, float, float, float]] = []
    tol = 0.05 / k
    for c in sorted(cands, key=lambda c: -c[4]):
        cx0, cy0, cx1, cy1, _ = c
        dup = False
        for kx0, ky0, kx1, ky1, _a in keep:
            if cx0 >= kx0 - tol and cy0 >= ky0 - tol and cx1 <= kx1 + tol and cy1 <= ky1 + tol:
                dup = True
                break
            # recouvrement majoritaire (même baie dessinée deux fois)
            ox = max(0.0, min(cx1, kx1) - max(cx0, kx0))
            oy = max(0.0, min(cy1, ky1) - max(cy0, ky0))
            if ox * oy > 0.6 * (cx1 - cx0) * (cy1 - cy0):
                dup = True
                break
        if not dup:
            keep.append(c)
    return round(sum(c[4] for c in keep), 1), len(keep)


def _contre_terre_elevation(msp, k: float, gab: tuple[float, float, float, float]) -> float:
    """Partie de façade sous la ligne de terrain, MESURÉE sur l'élévation (m²).

    On échantillonne la cote du terrain (calque 401, y compris contours de
    hachures) sur la largeur de la façade : terrain(x) = y max ; la surface
    enterrée visible = intégrale de (terrain − pied de façade)."""
    x0, y0, x1, y1 = gab
    samples: list[tuple[float, float]] = []
    for e in msp:
        lyr = _layer_of(e)
        if not _LYR_TERRAIN.search(lyr) or re.search(r"parcelle|limite", lyr, re.I):
            continue
        for (px, py) in _pts_of(e):
            if x0 <= px <= x1:
                samples.append((px, min(py, y1)))
    if len(samples) < 2:
        return 0.0
    nbins = 60
    binw = (x1 - x0) / nbins
    if binw <= 0:
        return 0.0
    grade: dict[int, float] = {}
    for px, py in samples:
        b = min(int((px - x0) / binw), nbins - 1)
        grade[b] = max(grade.get(b, -1e18), py)
    area = 0.0
    for b, gy in grade.items():
        if gy > y0:
            area += (gy - y0) * binw
    return round(area * k * k, 1)


# ---------------------------------------------------------------------------
# Extraction principale (conversion minimale)
# ---------------------------------------------------------------------------
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
    return _extract_doc(doc, msp, filename)


def _extract_doc(doc, msp, filename: str) -> dict:
    plan_type, orientation = detect_plan_type(filename)
    k = _unit_to_m(doc)

    xs: list[float] = []
    ys: list[float] = []
    fxs: list[float] = []   # bornes du revêtement de façade (gabarit précis)
    fys: list[float] = []
    roof_area = 0.0
    roof_perim = 0.0
    slab_area = 0.0
    sre_labeled: list[float] = []  # surfaces étiquetées « Surface … » (officielles)
    sre_bare: list[float] = []     # nombres nus « N m² » (fallback)
    non_chauffe: list[tuple[str, float]] = []  # locaux non chauffés étiquetés
    isol_ys: list[float] = []      # isolation périphérique (coupes) → prof. enterrée
    window_count = 0
    window_area = 0.0
    notes = []

    for e in msp:
        lyr = _layer_of(e)
        dt = e.dxftype()

        # Isolation périphérique (coupes) — AVANT le filtre bruit (104 non exclu,
        # mais soyons explicites) : sa hauteur ≈ profondeur enterrée.
        if plan_type == "coupe" and _LYR_ISOL_PERIPH.search(lyr):
            bb = _bbox_of(e)
            if bb:
                isol_ys += [bb[1], bb[3]]

        if _LYR_SKIP.search(lyr):
            continue

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

        # Gabarit de façade : bornes du revêtement (calque dédié) via bbox réelle
        if _LYR_FACADE_SURF.search(lyr):
            bb = _bbox_of(e)
            if bb:
                fxs += [bb[0], bb[2]]
                fys += [bb[1], bb[3]]

        # Toiture : plus grande polyligne fermée sur calque toiture (+ périmètre)
        if _LYR_TOITURE.search(lyr) and dt in ("LWPOLYLINE", "POLYLINE"):
            if getattr(e, "closed", False) or getattr(getattr(e, "dxf", None), "flags", 0):
                a = _poly_area_m2(e, k or 0.001)
                if a > roof_area:
                    roof_area = a
                    roof_perim = _poly_perimeter_m(e, k or 0.001)

        # Dalles : somme des polylignes fermées sur calque dalle
        if _LYR_DALLE.search(lyr) and dt in ("LWPOLYLINE", "POLYLINE") and getattr(e, "closed", False):
            slab_area += _poly_area_m2(e, k or 0.001)

        # Fenêtres : blocs (INSERT) sur calque/nom fenêtre
        if dt == "INSERT":
            try:
                name = e.dxf.name or ""
            except Exception:
                name = ""
            if _LYR_FENETRE.search(lyr) or _LYR_FENETRE.search(name):
                window_count += 1
                bb = _bbox_of(e)
                if bb:
                    w = (bb[2] - bb[0]) * (k or 0.001)
                    h = (bb[3] - bb[1]) * (k or 0.001)
                    if 0.1 < w < 6 and 0.1 < h < 6:
                        window_area += w * h

        # Zones → SRE : texte de surface sur calque zone. Étiquettes architecte
        # (« Surface SBP … ») prioritaires sur les nombres nus ; les locaux non
        # chauffés sont collectés à part (→ planchers sur local non chauffé).
        if dt in ("TEXT", "MTEXT") and _LYR_ZONE.search(lyr):
            t = _mtext_plain(e)
            m = _AIRE_RE.search(t)
            if m:
                try:
                    val = float(m.group(1).replace(",", "."))
                except ValueError:
                    continue
                if _NON_CHAUFFE.search(t):
                    non_chauffe.append((t.strip()[:40], val))
                elif re.search(r"surface|sre|sbp|\bsu\b", t, re.I):
                    sre_labeled.append(val)
                else:
                    sre_bare.append(val)

    # Si unité inconnue, devine (mm si étendue énorme)
    unit_guessed = False
    if not k and (xs or fxs):
        allx = xs + fxs
        ally = ys + fys
        span = max(max(allx) - min(allx), max(ally) - min(ally))
        k = 0.001 if span > 2000 else 1.0
        unit_guessed = True
        notes.append("unité non déclarée — supposée " + ("mm" if k == 0.001 else "m"))
    k = k or 0.001

    # Confiance : « haute » si l'unité du dessin est déclarée et les mesures
    # géométriques cohérentes ; « moyenne » si l'unité a dû être déduite (cas
    # fréquent des exports DWG) — les mesures restent cohérentes entre elles.
    confiance = "moyenne" if unit_guessed else "haute"

    out: dict = {
        "plan_type": plan_type,
        "orientation": orientation,
        "methode": "mesure CAO (DXF)",
        "confiance": confiance,
        "remarques": "; ".join(notes) or "géométrie vectorielle mesurée",
        "sre_contribution_m2": None,
        "surface_toiture_m2": None,
        "surface_facade_brute_m2": None,
        "surface_fenetres_m2": None,
        "surface_facade_contre_terre_m2": None,
        "surface_plancher_ext_terre_m2": None,
        "ponts_thermiques": [],
    }

    # Gabarit façade : le revêtement (116) prime sur l'enveloppe des porteurs.
    gx, gy = (fxs, fys) if fxs else (xs, ys)
    if plan_type == "facade" and gx:
        x0, x1 = min(gx), max(gx)
        y0, y1 = min(gy), max(gy)
        w = (x1 - x0) * k
        h = (y1 - y0) * k
        if 1 < w < 200 and 1 < h < 100:
            out["surface_facade_brute_m2"] = round(w * h, 1)
            if fxs:
                out["remarques"] += " — gabarit mesuré sur le revêtement de façade"
            # Baies mesurées sur l'élévation (polylignes de menuiseries)
            baies, nb = _baies_elevation(msp, k, (x0, y0, x1, y1))
            if baies > 0:
                out["surface_fenetres_m2"] = baies
                out["remarques"] += f" — {nb} baie(s) mesurée(s) sur l'élévation"
            elif window_area > 0:
                out["surface_fenetres_m2"] = round(window_area, 1)
            elif window_count:
                out["remarques"] += f" — {window_count} fenêtre(s) détectée(s), surface à confirmer"
            # Partie contre terre visible (ligne de terrain de l'élévation)
            ct = _contre_terre_elevation(msp, k, (x0, y0, x1, y1))
            if ct >= 0.5:
                out["surface_facade_contre_terre_m2"] = ct
                out["remarques"] += " — partie enterrée mesurée sous la ligne de terrain"

    if plan_type == "toiture" and roof_area > 0:
        out["surface_toiture_m2"] = round(roof_area, 1)
        if roof_perim > 0:
            out["ponts_thermiques"].append({
                "type": "acrotère / rive de toiture (périmètre toiture mesuré)",
                "longueur_m": round(roof_perim, 1),
            })

    if plan_type in ("etage", "sous_sol"):
        # Valeurs étiquetées par l'architecte si présentes, sinon nombres nus.
        sre_vals = sre_labeled or sre_bare
        if sre_vals:
            out["sre_contribution_m2"] = round(sum(sre_vals), 1)
            if not sre_labeled:
                out["remarques"] += " — surfaces non étiquetées, à confirmer"
        if plan_type == "sous_sol":
            # Radier du niveau enterré = plancher contre terre.
            base = slab_area if slab_area > 0 else (sum(sre_vals) if sre_vals else 0)
            if base > 0:
                out["surface_plancher_ext_terre_m2"] = round(base, 1)
                out["remarques"] += " — radier (plancher contre terre)"
        elif non_chauffe:
            # Plancher du niveau supérieur posé sur un local non chauffé (couvert…)
            tot = round(sum(v for _, v in non_chauffe), 1)
            out["surface_plancher_ext_terre_m2"] = tot
            noms = ", ".join(n for n, _ in non_chauffe)
            out["remarques"] += f" — plancher sur local non chauffé : {noms} ({tot} m²)"

    if plan_type == "coupe" and isol_ys:
        prof = (max(isol_ys) - min(isol_ys)) * k
        if 0.8 <= prof <= 6.0:
            out["profondeur_enterree_m"] = round(prof, 2)
            out["remarques"] += f" — profondeur enterrée mesurée (isolation périphérique) : {prof:.2f} m"

    # Fenêtres détectées sur un plan non-façade : on les remonte aussi si orientées
    if plan_type != "facade" and window_area > 0 and orientation:
        out["surface_fenetres_m2"] = round(window_area, 1)

    # Normalise les numériques (évite que des float numpy fuient en JSON/DB).
    for kk in ("sre_contribution_m2", "surface_toiture_m2", "surface_facade_brute_m2",
               "surface_fenetres_m2", "surface_facade_contre_terre_m2", "surface_plancher_ext_terre_m2"):
        if out[kk] is not None:
            out[kk] = float(out[kk])
    return out


# ---------------------------------------------------------------------------
# Réparation du DXF LibreDWG + lecture complète (blocs, tampons de zone)
# ---------------------------------------------------------------------------
_INT_LINE = re.compile(rb"^\s*[+-]?\d+\s*$")
_TABLE_ENTRIES = {b"LAYER", b"STYLE", b"LTYPE", b"APPID", b"DIMSTYLE",
                  b"VPORT", b"UCS", b"VIEW", b"BLOCK_RECORD"}


def repair_libredwg_dxf(data: bytes) -> bytes:
    """Répare les défauts de sérialisation DXF de LibreDWG.

    1. Valeurs multi-lignes : LibreDWG écrit parfois une valeur (MTEXT « 15.1 m² »
       avec exposant, police…) sur plusieurs lignes → désynchronise l'alternance
       code/valeur. Dans un DXF sain, deux lignes non-entières consécutives sont
       impossibles : la seconde est donc une continuation, qu'on replie.
    2. Entrées de table sans nom : une entrée TABLES sans tag 2 fait échouer le
       parseur ; on injecte un nom de secours.
    """
    nl = b"\r\n" if b"\r\n" in data[:2000] else b"\n"
    lines = data.split(nl)
    out: list[bytes] = []
    for ln in lines:
        if out and not _INT_LINE.match(ln) and not _INT_LINE.match(out[-1]):
            out[-1] += b" " + ln
        else:
            out.append(ln)

    res: list[bytes] = []
    i, in_tables, fixes, n = 0, False, 0, len(out)
    while i < n:
        if out[i].strip() == b"0" and i + 1 < n:
            nxt = out[i + 1].strip()
            if nxt == b"SECTION" and i + 3 < n and out[i + 2].strip() == b"2":
                in_tables = out[i + 3].strip() == b"TABLES"
            elif nxt == b"ENDSEC":
                in_tables = False
            elif in_tables and nxt in _TABLE_ENTRIES:
                j = i + 2
                has_name = False
                while j + 1 < n and out[j].strip() != b"0":
                    if out[j].strip() == b"2" and out[j + 1].strip():
                        has_name = True
                        break
                    j += 2
                if not has_name:
                    fixes += 1
                    res += [out[i], out[i + 1], b"  2", b"_LESO_FIX_%d" % fixes]
                    i += 2
                    continue
        res.append(out[i])
        i += 1
    return nl.join(res)


def _full_repaired_doc(dwg_bytes: bytes):
    """Conversion COMPLÈTE (non minimale) + réparation → document ezdxf, ou None."""
    import os
    conv = os.environ.get("LIBREDWG_DWG2DXF") or _which("dwg2dxf")
    if not conv:
        return None
    data = _run_dwg2dxf(conv, dwg_bytes, None, minimal=False)
    if not data:
        return None
    try:
        from ezdxf import recover
        doc, _ = recover.read(BytesIO(repair_libredwg_dxf(data)))
        return doc
    except Exception as exc:
        logger.debug("Lecture complète (réparée) échouée : %s", exc)
        return None


def _zone_stamps(doc, k: float) -> list[tuple[float, str]]:
    """Tampons de zone ArchiCAD : (surface m², nom de pièce le plus proche).

    Les surfaces des pièces sont des MTEXT (calque « Marques de Zone ») souvent
    orphelins dans l'export ; les noms vivent dans des blocs définis en
    coordonnées monde. On apparie par proximité spatiale."""
    areas: list[tuple[float, tuple[float, float]]] = []
    names: list[tuple[str, tuple[float, float]]] = []

    def pos_of(e):
        try:
            p = e.dxf.insert
            return (p.x, p.y)
        except Exception:
            return None

    for e in doc.entitydb.values():
        if e.dxftype() != "MTEXT":
            continue
        # plain_text() laisse parfois des résidus de mise en forme (exposant ²
        # rendu « ^ », antislashs) : on les neutralise avant d'apparier.
        t = re.sub(r"[\^\\]+", " ", _mtext_plain(e)).strip()
        if not t:
            continue
        m = re.search(r"(\d{1,4}[.,]\d{1,2})\s*m\s*[²2]?(\s|$)", t)
        p = pos_of(e)
        if m and re.search(r"m\s*[²2]|m2", t):
            try:
                areas.append((float(m.group(1).replace(",", ".")), p or (0, 0)))
            except ValueError:
                pass
        elif p and len(t) >= 2 and not re.match(r"^[\d\s.,+-]+$", t):
            names.append((t[:40], p))

    out: list[tuple[float, str]] = []
    for a, ap in areas:
        best, bd = "", 5.0 / (k or 0.001)   # rayon d'appariement : 5 m
        for nm, np_ in names:
            d = math.dist(ap, np_)
            if d < bd:
                best, bd = nm, d
        out.append((a, best))
    return out


def _walls_footprint(doc, k: float) -> tuple[float, float, float] | None:
    """Empreinte (l, L, périmètre) du bâti d'un PLAN : union des blocs de murs
    (exports ArchiCAD : blocs « Mur_* » définis en coordonnées monde)."""
    xs: list[float] = []
    ys: list[float] = []
    try:
        from ezdxf.bbox import extents
        for blk in doc.blocks:
            if not re.match(r"(Mur_|Poteau_)", blk.name):
                continue
            bb = extents(e for e in blk if e.dxftype() != "INSERT")
            if bb.has_data:
                xs += [bb.extmin.x, bb.extmax.x]
                ys += [bb.extmin.y, bb.extmax.y]
    except Exception:
        return None
    if not xs:
        return None
    w = (max(xs) - min(xs)) * k
    h = (max(ys) - min(ys)) * k
    if not (3 < w < 200 and 3 < h < 200):
        return None
    return round(w, 1), round(h, 1), round(2 * (w + h), 1)


def extract_from_dwg(dwg_bytes: bytes, filename: str) -> dict | None:
    """Extraction complète d'une planche DWG : conversion minimale (mesures sur
    calques) + conversion complète réparée (tampons de zone, empreinte des murs).
    """
    dxf = dwg_to_dxf_bytes(dwg_bytes)
    out = extract_from_dxf(dxf, filename) if dxf else None

    plan_type, _ = detect_plan_type(filename)
    need_full = plan_type in ("etage", "sous_sol") and (
        out is None or out.get("sre_contribution_m2") is None
        or out.get("plan_type") in ("etage", "sous_sol")
    )
    if not need_full:
        return out

    full = _full_repaired_doc(dwg_bytes)
    if full is None:
        return out
    k = _unit_to_m(full) or 0.001

    if out is None:
        out = {
            "plan_type": plan_type, "orientation": None,
            "methode": "mesure CAO (DXF)", "confiance": "moyenne",
            "remarques": "lecture via conversion complète réparée",
            "sre_contribution_m2": None, "surface_toiture_m2": None,
            "surface_facade_brute_m2": None, "surface_fenetres_m2": None,
            "surface_facade_contre_terre_m2": None,
            "surface_plancher_ext_terre_m2": None, "ponts_thermiques": [],
        }

    # SRE de secours : somme des tampons de zone des pièces chauffées.
    if out.get("sre_contribution_m2") is None:
        stamps = _zone_stamps(full, k)
        if stamps:
            heated = [a for a, nm in stamps
                      if not _NON_CHAUFFE.search(nm or "")]
            nch = [(nm, a) for a, nm in stamps if nm and _NON_CHAUFFE.search(nm)]
            if heated:
                out["sre_contribution_m2"] = float(round(sum(heated), 1))
                out["confiance"] = "moyenne"
                out["remarques"] += (
                    f" — SRE = somme des {len(heated)} pièces (tampons de zone, surfaces nettes)"
                    " ; à majorer de l'épaisseur des murs"
                )
            if nch and out.get("surface_plancher_ext_terre_m2") is None:
                tot = round(sum(a for _, a in nch), 1)
                out["surface_plancher_ext_terre_m2"] = float(tot)
                out["remarques"] += f" — locaux non chauffés : {tot} m²"

    # Périmètre d'étage (jonction dalle-façade) / du sous-sol (mur enterré).
    fp = _walls_footprint(full, k)
    if fp:
        w, h, perim = fp
        out["perimetre_m"] = perim
        label = ("jonction radier / mur enterré (périmètre sous-sol mesuré)"
                 if plan_type == "sous_sol"
                 else "jonction dalle intermédiaire / façade (périmètre étage mesuré)")
        out["ponts_thermiques"] = (out.get("ponts_thermiques") or []) + [
            {"type": label, "longueur_m": perim},
        ]
        out["remarques"] += f" — empreinte murs {w}×{h} m (périmètre {perim} m)"
    return out


# ---------------------------------------------------------------------------
# Conversion DWG → DXF (LibreDWG)
# ---------------------------------------------------------------------------
# Versions DXF essayées par dwg2dxf. La sérialisation DXF de LibreDWG est
# inégale selon la version cible ; la « meilleure » varie d'un fichier à l'autre,
# donc on convertit dans plusieurs versions et on retient celle qui se parse avec
# le plus d'entités. None = version native du DWG.
_DWG_VERSIONS: tuple[str | None, ...] = (None, "r2000", "r2013")


def _dxf_entity_count(dxf_bytes: bytes) -> int:
    """Nombre d'entités modelspace si ezdxf parse le DXF, sinon -1 (illisible)."""
    try:
        from ezdxf import recover
        doc, _ = recover.read(BytesIO(dxf_bytes))
        return sum(1 for _ in doc.modelspace())
    except Exception:
        return -1


def _run_dwg2dxf(conv: str, dwg_bytes: bytes, version: str | None,
                 minimal: bool = True) -> bytes | None:
    """Une conversion dwg2dxf. En mode minimal (HEADER+ENTITIES), la section
    TABLES — souvent mal sérialisée par LibreDWG — est sautée ; les calques
    restent lisibles sur les entités."""
    import os
    import subprocess
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.dwg")
            dst = os.path.join(d, "out.dxf")
            with open(src, "wb") as f:
                f.write(dwg_bytes)
            cmd = [conv, "-y"]
            if minimal:
                cmd.insert(1, "-m")
            if version:
                cmd[1:1] = ["--as", version]
            cmd += ["-o", dst, src]
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
            if os.path.exists(dst):
                with open(dst, "rb") as f:
                    return f.read()
    except Exception as exc:
        # Échec attendu pour certaines versions cibles (toutes ne savent pas
        # sérialiser un DWG donné) ; dwg_to_dxf_bytes essaie les autres.
        logger.debug("Conversion DWG→DXF (%s) échouée : %s", version or "native", exc)
    return None


def dwg_to_dxf_bytes(dwg_bytes: bytes) -> bytes | None:
    """Convertit un DWG en DXF si le binaire dwg2dxf (LibreDWG) est disponible.

    On essaie plusieurs versions cibles et on retient le DXF qui se parse avec le
    plus d'entités (la qualité de sortie de LibreDWG dépend de la version)."""
    import os
    conv = os.environ.get("LIBREDWG_DWG2DXF") or _which("dwg2dxf")
    if not conv:
        return None
    best: bytes | None = None
    best_score = 0  # il faut au moins 1 entité lisible
    for ver in _DWG_VERSIONS:
        data = _run_dwg2dxf(conv, dwg_bytes, ver)
        if not data:
            continue
        score = _dxf_entity_count(data)
        if score > best_score:
            best_score, best = score, data
    return best


def _which(name: str) -> str | None:
    import shutil
    return shutil.which(name)


def dxf_to_png_b64(dxf_bytes: bytes, max_px: int = 2000) -> str | None:
    """Rend un DXF en image (JPEG base64) cadrée sur le bâtiment, pour la lecture
    vision. On exclut le bruit (végétation, parcelles, cotation…) du cadrage afin
    que la planche soit nette et lisible par l'IA (fenêtres, ligne de terrain,
    ponts thermiques en coupe — grandeurs non déductibles de la seule géométrie).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from ezdxf import recover
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        from ezdxf.bbox import extents
        from PIL import Image
    except Exception as exc:  # dépendances de rendu absentes
        logger.warning("Rendu DXF→image indisponible : %s", exc)
        return None

    try:
        doc, _ = recover.read(BytesIO(dxf_bytes))
        msp = doc.modelspace()

        # On ne dessine QUE le bâti (hors bruit : végétation, parcelles, cotation,
        # légendes…) et on CADRE sur les calques structurels (murs, façade, dalles,
        # toiture, zones) pour éviter qu'un repère/élément lointain ne réduise le
        # bâtiment à un point.
        drawn = [e for e in msp if not _LYR_SKIP.search(_layer_of(e))]
        xs: list[float] = []
        ys: list[float] = []
        for e in drawn:
            if not _LYR_FRAME.search(_layer_of(e)):
                continue
            try:
                bb = extents([e])
                if bb.has_data:
                    xs += [bb.extmin.x, bb.extmax.x]
                    ys += [bb.extmin.y, bb.extmax.y]
            except Exception:
                pass

        fig = plt.figure(dpi=150)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        backend = MatplotlibBackend(ax)
        Frontend(RenderContext(doc), backend).draw_entities(drawn)
        backend.finalize()
        if xs and ys:
            mx = (max(xs) - min(xs)) * 0.04 + 1
            my = (max(ys) - min(ys)) * 0.04 + 1
            ax.set_xlim(min(xs) - mx, max(xs) + mx)
            ax.set_ylim(min(ys) - my, max(ys) + my)
        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor="white", dpi=150)
        plt.close(fig)

        img = Image.open(BytesIO(buf.getvalue())).convert("RGB")
        img.thumbnail((max_px, max_px))
        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
        return base64.b64encode(out.getvalue()).decode("ascii")
    except Exception as exc:
        logger.warning("Rendu DXF→image échoué : %s", exc)
        return None
