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
    province: str = ""


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
            zg = geo.trouver_zone(c.province, c.zs) if c.zs else None
            cand = par_zs.get((prov, zs)) or par_zs.get(("", zs)) or ([(zg["c"][1], zg["c"][0])] if zg else [])
            if not cand:
                sans.append(c)
                continue
            ll = (sum(x for x, _ in cand) / len(cand), sum(y for _, y in cand) / len(cand))
            key, nom, src = ("zs", zs), f"ZS {c.zs}", "centre de la ZS"
        p = pts.setdefault(key, Point(ll[0], ll[1], nom, (ga or {}).get("z") or c.zs, source=src,
                                      province=(ga or {}).get("p") or c.province or (geo.provinces_de_zone(c.zs) or [""])[0]))
        if ga:
            p.aire_geo = ga
        p.cas.append(c)
        d, _ = IND.date_notification(c)
        if d and (not p.dernier or d > p.dernier):
            p.dernier = d
    return Carte(list(pts.values()), sans, len(coords))


# classes de délai depuis le dernier cas notifié (jours) : (jusqu'à, couleur, libellé de légende)
CLASSES = [(3, "#9B1B1B", "0 à 3 jours"), (7, "#E0492B", "4 à 7 jours"), (14, "#F28C28", "8 à 14 jours"),
           (21, "#F2C94C", "15 à 21 jours"), (None, "#5E9E6E", "plus de 21 jours")]


def couleur(jours: Optional[int]) -> str:
    """Couleur selon le délai depuis le dernier cas : 0-3, 4-7, 8-14, 15-21, plus de 21 jours."""
    if jours is None:
        return theme.GREY
    for fin, c, _l in CLASSES:
        if fin is None or jours <= fin:
            return c
    return CLASSES[-1][1]


def legende() -> list:
    """[(couleur, libellé traduit)] des classes de délai."""
    from core.langue import tr
    return [(c, tr(l)) for _f, c, l in CLASSES]


def svg(carte: Carte, ref: Optional[date] = None, width: int = 980, height: int = 640, vue: str = "cas",
        niveau: str = "", province: str = "", zs: str = "", lien=None) -> str:
    """Carte des cas : nationale (provinces), d'une province (zones de santé) ou d'une zone (aires de santé),
    sur les contours réels ; sans contours, sur un quadrillage."""
    ref = ref or date.today()
    if geo.niveaux()["provinces"]:
        if not niveau:          # ancien appel : vue autour des cas
            provs = sorted({p.province for p in carte.points if p.province})
            zss = sorted({(p.province, p.zs) for p in carte.points if p.province})
            niveau, province, zs = (("zone", zss[0][0], zss[0][1]) if len(zss) == 1 else
                                    ("province", provs[0], "") if len(provs) == 1 else ("national", "", ""))
        return svg_niveau(carte, niveau, province, zs, ref, lien=lien)
    return _svg_simple(carte, ref, width, height)


def _recence(cas: List[Case], ref: date) -> Optional[int]:
    """Jours depuis le dernier cas notifié du groupe (None si aucune date)."""
    ds = [d for d in (IND.date_notification(c)[0] for c in cas) if d]
    return (ref - max(ds)).days if ds else None


def svg_niveau(carte: Carte, niveau: str, province: str = "", zs: str = "", ref: Optional[date] = None,
               width: int = 1000, height: int = 700, lien=None) -> str:
    """niveau « national » : provinces ; « province » : zones de santé de la province ; « zone » : aires de santé.
    Couleur : délai depuis le dernier cas notifié. `lien(niveau, province, zs)` → adresse du niveau inférieur."""
    import math
    from core.langue import tr, trf
    e = html.escape
    ref = ref or date.today()
    N = geo.niveaux()
    cp, cz = _k(province)[0], _k(zs)[0]
    pts = carte.points
    if niveau == "zone":
        zone = geo.trouver_zone(province, zs)
        aires = [a for a in geo.aires_province(province) if _k(a["z"])[0] == cz]
        formes = [{"nom": a["a"], "anneaux": [r for poly in a["polys"] for r in poly], "c": a["c"], "bb": a["bb"],
                   "cle": (_k(a["z"])[0], _k(a["a"])[0])} for a in aires]
        cadre = [zone] if zone else []
        groupe = lambda p: (_k(p.aire_geo["z"])[0], _k(p.aire_geo["a"])[0]) if p.aire_geo else None
        pts = [p for p in pts if _k(p.zs)[0] == cz and (not cp or _k(p.province)[0] == cp)]
    elif niveau == "province":
        zones = [z for z in N["zones"] if _k(z["p"])[0] == cp]
        formes = [{"nom": z["z"], "anneaux": z["r"], "c": z["c"], "bb": z["bb"], "cle": _k(z["z"])[0]} for z in zones]
        cadre = [x for x in N["provinces"] if _k(x["p"])[0] == cp]
        groupe = lambda p: _k(p.zs)[0]
        pts = [p for p in pts if _k(p.province)[0] == cp]
    else:
        niveau = "national"
        formes = [{"nom": x["p"], "anneaux": x["r"], "c": x["c"], "bb": x["bb"], "cle": _k(x["p"])[0]}
                  for x in N["provinces"]]
        cadre = []
        groupe = lambda p: _k(p.province)[0]
    if not formes:
        return '<p class="muted">' + e(tr("Contours introuvables pour ce niveau.")) + "</p>"
    par_forme: Dict = {}
    for p in pts:
        g = groupe(p)
        if g is not None:
            par_forme.setdefault(g, []).extend(p.cas)
    x0 = min(f["bb"][0] for f in formes); y0 = min(f["bb"][1] for f in formes)
    x1 = max(f["bb"][2] for f in formes); y1 = max(f["bb"][3] for f in formes)
    m = 0.02 * max(x1 - x0, y1 - y0)
    x0, y0, x1, y1 = x0 - m, y0 - m, x1 + m, y1 + m
    k = math.cos(math.radians((y0 + y1) / 2))
    haut = 46
    s = min((width - 24) / ((x1 - x0) * k), (height - haut - 24) / (y1 - y0))
    ox = (width - s * (x1 - x0) * k) / 2
    oy = haut + (height - haut - s * (y1 - y0)) / 2

    def P(lon, lat):
        return ox + (lon - x0) * k * s, oy + (y1 - lat) * s

    def chemin(anneaux):
        return "".join("M" + "L".join(f"{P(x, y)[0]:.1f} {P(x, y)[1]:.1f}" for x, y in r) + "Z" for r in anneaux)

    titre = {"national": tr("République démocratique du Congo : cas par province"),
             "province": trf("Province {p} : cas par zone de santé", p=province),
             "zone": trf("Zone de santé {z} ({p}) : cas par aire de santé", z=zs, p=province)}[niveau]
    n_cas = sum(len(v) for v in par_forme.values())
    sous = trf("{n} cas placés", n=n_cas) + " · " + tr("couleur : délai depuis le dernier cas notifié")
    out = [f'<svg class="carte-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" '
           f'style="max-width:{width}px; font-family:{e(theme.FONT_STACK)}; background:#F4F7FA; border-radius:10px; '
           f'touch-action:none" role="img" aria-label="{e(titre)}">',
           f'<rect width="{width}" height="{height}" fill="#F4F7FA"/>',
           f'<text x="18" y="24" font-size="17" font-weight="800" fill="#1F3A5F">{e(titre)}</text>',
           f'<text x="18" y="40" font-size="11.5" fill="#4A5868">{e(sous)}</text>',
           '<g class="carte-zoom">']
    for f in formes:
        cas = par_forme.get(f["cle"], [])
        j = _recence(cas, ref) if cas else None
        fill = couleur(j) if cas else "#FFFFFF"
        op = ".78" if cas else "1"
        info = f"{f['nom']} : " + (trf("{n} cas", n=len(cas)) + (
            " ; " + trf("dernier cas notifié il y a {j} j", j=j) if j is not None else "") if cas else tr("aucun cas"))
        url = None
        if lien and niveau == "national":
            url = lien("province", f["nom"], "")
        elif lien and niveau == "province":
            url = lien("zone", province, f["nom"])
        forme = (f'<path d="{chemin(f["anneaux"])}" fill="{fill}" fill-opacity="{op}" stroke="#8796A6" '
                 f'stroke-width="{1.1 if niveau == "national" else .8}" vector-effect="non-scaling-stroke" '
                 f'fill-rule="evenodd"><title>{e(info)}</title></path>')
        out.append(f'<a href="{e(url)}" class="carte-lien">{forme}</a>' if url else forme)
    for c in cadre:          # contour du niveau supérieur
        out.append(f'<path d="{chemin(c["r"])}" fill="none" stroke="#1F3A5F" stroke-width="2.4" '
                   'vector-effect="non-scaling-stroke" fill-rule="evenodd" style="pointer-events:none"/>')
    # ronds chiffrés : par forme (national, province) ou par aire / point GPS (zone)
    ronds = []
    if niveau == "zone":
        for p in pts:
            x, y = P(p.lon, p.lat)
            ronds.append({"x": x, "y": y, "cas": p.cas, "nom": p.nom})
    else:
        for f in formes:
            cas = par_forme.get(f["cle"], [])
            if cas:
                x, y = P(*f["c"])
                ronds.append({"x": x, "y": y, "cas": cas, "nom": f["nom"]})
    for r in ronds:
        r["r"] = 8 + 3.4 * (len(r["cas"]) ** 0.5)
    for _ in range(40):           # ronds voisins : écartés pour ne pas se recouvrir
        bouge = False
        for a in range(len(ronds)):
            for b in range(a + 1, len(ronds)):
                A, B = ronds[a], ronds[b]
                dx, dy = B["x"] - A["x"], B["y"] - A["y"]
                d = math.hypot(dx, dy) or 0.01
                mini = A["r"] + B["r"] + 3
                if d < mini:
                    pousse = (mini - d) / 2
                    ux, uy = (dx / d, dy / d) if d > 0.01 else (1.0, 0.0)
                    A["x"] -= ux * pousse; A["y"] -= uy * pousse
                    B["x"] += ux * pousse; B["y"] += uy * pousse
                    bouge = True
        if not bouge:
            break
    # noms des formes sans cas (au centre, si la forme est assez grande et si la place est libre)
    avec_cas = {r["nom"] for r in ronds}
    pris = []
    for R in ronds:
        lw = len(R["nom"]) * 12 * 0.62 / 2
        pris.append((R["x"] - max(R["r"], lw), R["y"] - R["r"] - 18, R["x"] + max(R["r"], lw), R["y"] + R["r"]))

    def libre(b):
        return all(b[2] < q[0] or b[0] > q[2] or b[3] < q[1] or b[1] > q[3] for q in pris)
    for f in formes:
        if f["nom"] in avec_cas or par_forme.get(f["cle"]):
            continue
        x, y = P(*f["c"])
        w_px = (f["bb"][2] - f["bb"][0]) * k * s
        taille = 10.5 if niveau != "zone" else 9.5
        lw = len(f["nom"]) * taille * 0.56
        if lw > w_px * 0.95:
            continue
        boite = (x - lw / 2, y - taille, x + lw / 2, y + 4)
        if not libre(boite):
            continue
        pris.append(boite)
        out.append(f'<text class="fixe" data-x="{x:.1f}" data-y="{y:.1f}" x="{x:.1f}" y="{y + 3:.1f}" font-size="{taille}" '
                   f'text-anchor="middle" font-weight="500" fill="#5F6B7A" paint-order="stroke" stroke="#fff" '
                   f'stroke-width="3" style="pointer-events:none">{e(f["nom"])}</text>')
    # ronds et noms en gras au-dessus de chaque rond
    for R in sorted(ronds, key=lambda r: -len(r["cas"])):
        x, y, r, cas = R["x"], R["y"], R["r"], R["cas"]
        j = _recence(cas, ref)
        dc = sum(1 for c in cas if c.issue == "Décès")
        codes = ", ".join(c.code_cas or "?" for c in cas[:12]) + (" …" if len(cas) > 12 else "")
        info = f"{R['nom']} : " + trf("{n} cas, {d} décès", n=len(cas), d=dc) + f"\n{codes}"
        out.append(f'<g class="fixe" data-x="{x:.1f}" data-y="{y:.1f}" style="pointer-events:none">'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{couleur(j)}" stroke="#fff" stroke-width="2"/>'
                   f'<text x="{x:.1f}" y="{y + 4:.1f}" font-size="11.5" font-weight="800" text-anchor="middle" fill="#fff">'
                   f'{len(cas)}</text>'
                   f'<text x="{x:.1f}" y="{y - r - 4:.1f}" font-size="{12 if niveau != "zone" else 11}" font-weight="800" '
                   f'text-anchor="middle" fill="#13243A" paint-order="stroke" stroke="#fff" stroke-width="3.2">'
                   f'{e(R["nom"].upper())}</text><title>{e(info)}</title></g>')
    out.append("</g>")
    # légende (dans l'image, pour le téléchargement)
    ly = height - 14
    lx = 18
    out.append(f'<text x="{lx}" y="{ly}" font-size="11.5" font-weight="700" fill="#1F2933">'
               f'{e(tr("Dernier cas :"))}</text>')
    lx += 12 + 6.4 * len(tr("Dernier cas :"))
    for c, t in legende() + [("#FFFFFF", tr("aucun cas"))]:
        out.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" rx="3" fill="{c}" fill-opacity=".9" '
                   f'stroke="#8796A6" stroke-width=".8"/><text x="{lx + 17}" y="{ly}" font-size="11.5" fill="#1F2933">{e(t)}</text>')
        lx += 30 + 6.2 * len(t)
    src = tr("Contours : aires de santé GRID3 / CIESIN, simplifiés ; Mapping Épi")
    out.append(f'<text x="{width - 14}" y="24" font-size="10" text-anchor="end" fill="#5F6B7A">{e(src)}</text>')
    out.append("</svg>")
    return "".join(out)


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
                  for c, t in legende())
    return "".join(out) + f'<div style="font-size:12.5px;margin-top:6px">{leg} · taille : nombre de cas</div>'
