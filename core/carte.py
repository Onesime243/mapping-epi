"""Carte des cas (hors ligne, sans fond de carte téléchargé).

Position de chaque cas, dans l'ordre :
1. coordonnées GPS saisies dans la fiche (latitude / longitude du cas) ;
2. coordonnées de son aire de santé (fichier de coordonnées des AS) ;
3. centre des aires connues de sa zone de santé.
Les cas sans position sont listés à part : rien n'est placé au hasard.

Fichier de coordonnées : CSV « province;zone_sante;aire_sante;latitude;longitude » (séparateur ; ou ,),
par exemple tiré des limites des aires de santé GRID3 / OCHA. Il s'importe depuis la page Carte
et est gardé dans le dossier de données (coordonnees_as.csv).
"""
from __future__ import annotations

import csv
import html
import io
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import theme
from core import geo
from core import indicateurs as IND
from core.models import Case

NOM_FICHIER = "coordonnees_as.csv"


def _k(*parts: str) -> Tuple[str, ...]:
    from core.lieux import cle
    return tuple(cle(p or "") for p in parts)


def fichier() -> Path:
    from core.paths import data_dir
    return data_dir() / NOM_FICHIER


def lire_coordonnees(texte: str) -> Dict[Tuple[str, str, str], Tuple[float, float]]:
    """Lit un CSV de coordonnées ; ignore les lignes invalides."""
    texte = texte.lstrip("﻿")
    sep = ";" if texte.count(";") >= texte.count(",") else ","
    out = {}
    for row in csv.DictReader(io.StringIO(texte), delimiter=sep):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        try:
            lat = float(row.get("latitude", row.get("lat", "")).replace(",", "."))
            lon = float(row.get("longitude", row.get("lon", "")).replace(",", "."))
        except ValueError:
            continue
        if not (-14 <= lat <= 6 and 11 <= lon <= 32):      # hors de la RDC : ligne ignorée
            continue
        zs = row.get("zone_sante") or row.get("zs") or ""
        aire = row.get("aire_sante") or row.get("as") or ""
        if zs:
            out[_k(row.get("province", ""), zs, aire)] = (lat, lon)
    return out


def coordonnees() -> Dict[Tuple[str, str, str], Tuple[float, float]]:
    f = fichier()
    if not f.exists():
        return {}
    try:
        return lire_coordonnees(f.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return {}


def enregistrer(texte: str) -> int:
    n = len(lire_coordonnees(texte))
    if n:
        fichier().write_text(texte.lstrip("﻿"), encoding="utf-8")
    return n


@dataclass
class Point:
    lat: float
    lon: float
    nom: str
    zs: str
    cas: List[Case] = field(default_factory=list)
    dernier: Optional[date] = None
    source: str = ""
    aire_geo: Optional[dict] = None


@dataclass
class Carte:
    points: List[Point]
    sans_position: List[Case]
    n_coord: int


def construire(cases: List[Case], coords=None) -> Carte:
    coords = coords if coords is not None else coordonnees()
    par_zs: Dict[Tuple[str, str], List[Tuple[float, float]]] = {}
    for (prov, zs, aire), ll in coords.items():
        par_zs.setdefault((prov, zs), []).append(ll)
    pts: Dict[Tuple, Point] = {}
    sans = []
    for c in cases:
        prov, zs, aire = _k(c.province, c.zs, c.aire_sante)
        ga = geo.trouver_aire(c.province, c.zs, c.aire_sante) if c.aire_sante else None
        if c.lat is not None and c.lon is not None:
            key, ll, nom, src = ("gps", round(c.lat, 3), round(c.lon, 3)), (c.lat, c.lon), c.aire_sante or c.zs, "GPS"
        elif ga:
            ll = (ga["c"][1], ga["c"][0])
            key, nom, src = ("as", zs, aire), ga["a"], "aire de santé"
        elif (prov, zs, aire) in coords or ("", zs, aire) in coords:
            ll = coords.get((prov, zs, aire)) or coords[("", zs, aire)]
            key, nom, src = ("as", zs, aire), c.aire_sante, "aire de santé"
        else:
            cand = par_zs.get((prov, zs)) or par_zs.get(("", zs)) or [
                (x["c"][1], x["c"][0]) for x in geo.charger()["aires"] if _k(x["z"])[0] == zs]
            if not cand:
                sans.append(c)
                continue
            ll = (sum(x for x, _ in cand) / len(cand), sum(y for _, y in cand) / len(cand))
            key, nom, src = ("zs", zs), f"ZS {c.zs}", "centre de la ZS"
        p = pts.setdefault(key, Point(ll[0], ll[1], nom, (ga or {}).get("z") or c.zs, source=src))
        if ga:
            p.aire_geo = ga
        p.cas.append(c)
        d, _ = IND.date_notification(c)
        if d and (not p.dernier or d > p.dernier):
            p.dernier = d
    return Carte(list(pts.values()), sans, len(coords))


def couleur(jours: Optional[int]) -> str:
    if jours is None:
        return theme.GREY
    return theme.RED if jours <= 7 else theme.ORANGE if jours <= 21 else theme.YELLOW if jours <= 42 else theme.GREEN


def svg(carte: Carte, ref: Optional[date] = None, width: int = 980, height: int = 640, vue: str = "cas") -> str:
    """Carte des cas : sur les contours des aires de santé quand ils sont connus, sinon sur un quadrillage."""
    ref = ref or date.today()
    G = geo.charger()
    if G["aires"] and carte.points:
        return _svg_contours(carte, ref, G, width, height, vue)
    return _svg_simple(carte, ref, width, height)


def _svg_contours(carte: Carte, ref: date, G: dict, width: int, height: int, vue: str) -> str:
    import math
    e = html.escape
    pts = carte.points
    # étendue : aires et points des cas (+ marge), ou provinces entières
    if vue == "province":
        provs = {_k(p.aire_geo["p"])[0] for p in pts if p.aire_geo} or {_k(a["p"])[0] for a in G["aires"]}
        bbs = [a["bb"] for a in G["aires"] if _k(a["p"])[0] in provs]
    else:
        bbs = [p.aire_geo["bb"] for p in pts if p.aire_geo] + [[p.lon, p.lat, p.lon, p.lat] for p in pts]
    x0 = min(b[0] for b in bbs); y0 = min(b[1] for b in bbs)
    x1 = max(b[2] for b in bbs); y1 = max(b[3] for b in bbs)
    marge = 0.04 if vue == "province" else max(0.12, 0.25 * max(x1 - x0, y1 - y0))
    x0, y0, x1, y1 = x0 - marge, y0 - marge, x1 + marge, y1 + marge
    k = math.cos(math.radians((y0 + y1) / 2))
    s = min((width - 20) / ((x1 - x0) * k), (height - 20) / (y1 - y0))
    ox = (width - s * (x1 - x0) * k) / 2
    oy = (height - s * (y1 - y0)) / 2

    def P(lon, lat):
        return ox + (lon - x0) * k * s, oy + (y1 - lat) * s

    def chemin(anneaux):
        d = []
        for r in anneaux:
            d.append("M" + "L".join(f"{P(x, y)[0]:.1f} {P(x, y)[1]:.1f}" for x, y in r) + "Z")
        return "".join(d)

    # aires touchées : dernier cas notifié
    touchees: Dict[int, Point] = {}
    for p in pts:
        if p.aire_geo:
            touchees[id(p.aire_geo)] = p
    visibles = [a for a in G["aires"] if a["bb"][2] >= x0 and a["bb"][0] <= x1 and a["bb"][3] >= y0 and a["bb"][1] <= y1]
    out = [f'<svg class="carte-svg" viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px; '
           f'font-family:{e(theme.FONT_STACK)}; background:#EEF3F7; border-radius:10px; touch-action:none" role="img" '
           f'aria-label="Carte des cas"><g class="carte-zoom">']
    for a in visibles:
        p = touchees.get(id(a))
        if p:
            j = (ref - p.dernier).days if p.dernier else None
            fill, op = couleur(j), ".55"
            titre = f"{a['a']} (ZS {a['z']}) : {len(p.cas)} cas ; dernier cas notifié " + (
                f"{p.dernier:%d/%m/%Y}" if p.dernier else "?")
        else:
            fill, op, titre = "#FFFFFF", "1", f"{a['a']} (ZS {a['z']})"
        out.append(f'<path d="{"".join(chemin(poly) for poly in a["polys"])}" fill="{fill}" fill-opacity="{op}" '
                   f'stroke="#9AA8B6" stroke-width=".5" vector-effect="non-scaling-stroke" fill-rule="evenodd"><title>{e(titre)}</title></path>')
    for l in G["limites_zs"]:
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in l[:: max(1, len(l) // 8)] + [l[-1]]):
            out.append('<polyline points="' + " ".join(f"{P(x, y)[0]:.1f},{P(x, y)[1]:.1f}" for x, y in l)
                       + '" fill="none" stroke="#3E5368" stroke-width="1.6" stroke-linejoin="round" '
                       'vector-effect="non-scaling-stroke"/>')
    # noms des zones de santé (centre de leurs aires visibles)
    zones: Dict[str, List[Tuple[float, float]]] = {}
    for a in visibles:
        zones.setdefault(a["z"], []).append(P(*a["c"]))
    zs_cas = {_k(p.zs)[0] for p in pts}
    for z, xy in zones.items():
        cx, cy = sum(x for x, _ in xy) / len(xy), sum(y for _, y in xy) / len(xy)
        fort = _k(z)[0] in zs_cas
        out.append(f'<text class="fixe" data-x="{cx:.1f}" data-y="{cy:.1f}" x="{cx:.1f}" y="{cy:.1f}" '
                   f'font-size="{12 if fort else 10}" text-anchor="middle" '
                   f'font-weight="{750 if fort else 500}" fill="{"#1F3A5F" if fort else "#6B7785"}" paint-order="stroke" '
                   f'stroke="#fff" stroke-width="3" style="pointer-events:none">{e(z.upper() if fort else z)}</text>')
    # cas : nombre au centre de l'aire (ou au point GPS)
    for p in sorted(pts, key=lambda p: -len(p.cas)):
        x, y = P(p.lon, p.lat)
        j = (ref - p.dernier).days if p.dernier else None
        r = 7 + 3.2 * (len(p.cas) ** 0.5)
        dc = sum(1 for c in p.cas if c.issue == "Décès")
        codes = ", ".join(c.code_cas or "?" for c in p.cas[:12]) + (" …" if len(p.cas) > 12 else "")
        quand = f"dernier cas notifié {p.dernier:%d/%m/%Y}" if p.dernier else "date inconnue"
        out.append(f'<g class="fixe" data-x="{x:.1f}" data-y="{y:.1f}"><circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{couleur(j)}" stroke="#fff" stroke-width="1.6"/>'
                   f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="11" font-weight="750" text-anchor="middle" fill="#fff">'
                   f'{len(p.cas)}</text><title>{e(p.nom)} (ZS {e(p.zs)}) : {len(p.cas)} cas, {dc} décès ; {quand} ; '
                   f'position : {e(p.source)}\n{e(codes)}</title></g>')
    out.append("</g></svg>")
    leg = "".join(f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px">'
                  f'<span style="width:12px;height:12px;border-radius:3px;background:{c}"></span>{t}</span>'
                  for c, t in ((theme.RED, "dernier cas ≤ 7 j"), (theme.ORANGE, "8 à 21 j"), (theme.YELLOW, "22 à 42 j"),
                               (theme.GREEN, "plus de 42 j")))
    return ("".join(out) + f'<div style="font-size:12.5px;margin-top:6px">{leg} · chiffre : nombre de cas · traits épais : '
            "limites des zones de santé · molette ou pincement pour zoomer, glisser pour déplacer</div>"
            '<div class="muted" style="font-size:11.5px">Contours des aires de santé : GRID3 / CIESIN, simplifiés.</div>')


def _svg_simple(carte: Carte, ref: date, width: int, height: int) -> str:
    e = html.escape
    if not carte.points:
        return ('<p class="muted">Aucun cas ne peut être placé : saisissez la latitude et la longitude dans les fiches, '
                "ou importez le fichier des coordonnées des aires de santé.</p>")
    lats = [p.lat for p in carte.points]
    lons = [p.lon for p in carte.points]
    pad = 0.15
    la0, la1 = min(lats) - pad, max(lats) + pad
    lo0, lo1 = min(lons) - pad, max(lons) + pad
    m = 40
    sx = (width - 2 * m) / max(lo1 - lo0, 1e-6)
    sy = (height - 2 * m) / max(la1 - la0, 1e-6)
    s = min(sx, sy)
    ox = (width - s * (lo1 - lo0)) / 2
    oy = (height - s * (la1 - la0)) / 2

    def xy(lat, lon):
        return ox + (lon - lo0) * s, height - (oy + (lat - la0) * s)

    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" style="max-width:{width}px; font-family:{e(theme.FONT_STACK)}"'
           f' role="img" aria-label="Carte des cas">',
           f'<rect width="{width}" height="{height}" rx="10" fill="currentColor" fill-opacity=".03"/>']
    step = 0.5 if (la1 - la0) > 2 else 0.25 if (la1 - la0) > 0.8 else 0.1
    v = round(la0 / step) * step
    while v <= la1:
        _x, y = xy(v, lo0)
        out.append(f'<line x1="0" x2="{width}" y1="{y:.1f}" y2="{y:.1f}" stroke="currentColor" stroke-opacity=".08"/>'
                   f'<text x="4" y="{y - 3:.1f}" font-size="9.5" fill="currentColor" fill-opacity=".45">{v:.2f}°</text>')
        v += step
    v = round(lo0 / step) * step
    while v <= lo1:
        x, _y = xy(la0, v)
        out.append(f'<line y1="0" y2="{height}" x1="{x:.1f}" x2="{x:.1f}" stroke="currentColor" stroke-opacity=".08"/>'
                   f'<text x="{x + 3:.1f}" y="{height - 4}" font-size="9.5" fill="currentColor" fill-opacity=".45">{v:.2f}°</text>')
        v += step
    for p in sorted(carte.points, key=lambda p: -len(p.cas)):
        x, y = xy(p.lat, p.lon)
        j = (ref - p.dernier).days if p.dernier else None
        r = 6 + 4 * (len(p.cas) ** 0.5)
        dc = sum(1 for c in p.cas if c.issue == "Décès")
        codes = ", ".join(c.code_cas or "?" for c in p.cas[:12]) + (" …" if len(p.cas) > 12 else "")
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{couleur(j)}" fill-opacity=".75" '
                   f'stroke="#fff" stroke-width="1.5"><title>{e(p.nom)} ({e(p.zs)}) : {len(p.cas)} cas, {dc} décès ; '
                   f'dernier cas notifié {p.dernier:%d/%m/%Y} ; position : {e(p.source)}\n{e(codes)}</title></circle>'
                   if p.dernier else
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{couleur(j)}" fill-opacity=".75" stroke="#fff" '
                   f'stroke-width="1.5"><title>{e(p.nom)} : {len(p.cas)} cas</title></circle>')
        out.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="11" font-weight="700" text-anchor="middle" '
                   f'fill="#fff">{len(p.cas)}</text>')
    # un seul nom par zone de santé (au-dessus de ses points) ; le nom de chaque aire s'affiche au survol
    groupes: Dict[str, List[Point]] = {}
    for p in carte.points:
        groupes.setdefault(p.zs or "?", []).append(p)
    for zs, ps in groupes.items():
        xs = [xy(p.lat, p.lon) for p in ps]
        cx = sum(x for x, _ in xs) / len(xs)
        top = min(y - (6 + 4 * (len(p.cas) ** 0.5)) for (x, y), p in zip(xs, ps))
        n = sum(len(p.cas) for p in ps)
        out.append(f'<text x="{cx:.1f}" y="{top - 6:.1f}" font-size="12.5" font-weight="700" text-anchor="middle" '
                   f'fill="currentColor" paint-order="stroke" stroke="var(--panel, #fff)" stroke-width="3">'
                   f'{e(zs)} ({n})</text>')
    out.append("</svg>")
    leg = "".join(f'<span style="display:inline-flex;align-items:center;gap:5px;margin-right:14px">'
                  f'<span style="width:12px;height:12px;border-radius:50%;background:{c}"></span>{t}</span>'
                  for c, t in ((theme.RED, "dernier cas ≤ 7 j"), (theme.ORANGE, "8 à 21 j"), (theme.YELLOW, "22 à 42 j"),
                               (theme.GREEN, "plus de 42 j")))
    return "".join(out) + f'<div style="font-size:12.5px;margin-top:6px">{leg} · taille : nombre de cas</div>'
