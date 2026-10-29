"""Carte du parcours : lieux reliés par des flèches numérotées dans l'ordre chronologique.

- Si au moins deux lieux ont des coordonnées GPS : projection géographique réelle
  (équirectangulaire, sans fond de carte → 100 % hors ligne), échelle en km.
- Sinon : schéma topologique (disposition automatique en serpentin).
Les déplacements du corps après le décès sont tracés en rouge pointillé.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from config import theme
from core import rules
from core.models import Case, Event
from render import svgkit as K
from render.html_renderer import date_label, render_svg_page
from render.icons import icon_group
from render.network import PLACE_ICON

NON_PATIENT = {"Investigation", "Laboratoire", "Riposte", "Prélèvement"}


@dataclass
class Leg:
    n: int
    src: str
    dst: str
    ev: Event
    corps: bool


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def build_legs(case: Case) -> Tuple[List[str], List[Leg]]:
    stops: List[Tuple[str, Event]] = []
    death = case.date_deces
    for ev in case.events:
        if ev.type in NON_PATIENT:
            continue
        for loc in (ev.lieu, ev.lieu_arrivee):
            if loc.strip() and (not stops or _norm(stops[-1][0]) != _norm(loc)):
                stops.append((loc.strip(), ev))
    order: List[str] = []
    for name, _ in stops:
        if all(_norm(name) != _norm(o) for o in order):
            order.append(name)
    legs: List[Leg] = []
    for i in range(1, len(stops)):
        src, dst, ev = stops[i - 1][0], stops[i][0], stops[i][1]
        corps = bool(ev.type in ("Décès", "Funérailles", "Enterrement") or (death and ev.date_debut and ev.date_debut > death)
                     or (ev.type == "Décès" and ev.lieu_arrivee))
        legs.append(Leg(i, src, dst, ev, corps))
    return order, legs


def _canon(name: str, order: List[str]) -> str:
    for o in order:
        if _norm(o) == _norm(name):
            return o
    return name


def _positions(case: Case, order: List[str], box) -> Tuple[Dict[str, Tuple[float, float]], Optional[float]]:
    x0, y0, w, h = box
    gps = {}
    for p in case.places:
        if p.lat is not None and p.lon is not None:
            gps[_norm(p.nom)] = (p.lat, p.lon)
    located = [o for o in order if _norm(o) in gps]
    if len(located) >= 2:
        lats = [gps[_norm(o)][0] for o in located]
        lons = [gps[_norm(o)][1] for o in located]
        lat0 = sum(lats) / len(lats)
        kx = math.cos(math.radians(lat0))
        minx, maxx = min(lons) * kx, max(lons) * kx
        miny, maxy = min(lats), max(lats)
        spanx, spany = max(maxx - minx, 1e-4), max(maxy - miny, 1e-4)
        scale = min((w - 160) / spanx, (h - 140) / spany)
        cx, cy = x0 + w / 2, y0 + h / 2
        pos = {}
        for o in located:
            la, lo = gps[_norm(o)]
            pos[o] = (cx + (lo * kx - (minx + maxx) / 2) * scale, cy - (la - (miny + maxy) / 2) * scale)
        # lieux sans GPS : alignés en bas
        rest = [o for o in order if o not in pos]
        for i, o in enumerate(rest):
            pos[o] = (x0 + 80 + i * 150, y0 + h - 40)
        km_per_px = 111.32 / scale
        return pos, km_per_px
    # disposition topologique : lieux sur une ellipse dans l'ordre de première visite
    # (les flèches deviennent des cordes qui ne traversent pas les autres lieux)
    n = len(order)
    cx, cy = x0 + w / 2, y0 + h / 2 - 10
    rx, ry = w / 2 - 110, h / 2 - 95
    pos = {}
    for i, o in enumerate(order):
        if n == 1:
            pos[o] = (cx, cy)
            continue
        a = math.pi + 2 * math.pi * i / n
        pos[o] = (cx + rx * math.cos(a), cy + ry * math.sin(a))
    return pos, None


def render_svg(case: Case) -> str:
    order, legs = build_legs(case)
    box = (30, 80, 820, 586)
    pos, kmpx = _positions(case, order, box)
    mode = "géographique (GPS)" if kmpx else "schématique (sans GPS)"
    out = [K.svg_open(), K.header(
        f"CARTE DU PARCOURS – CAS {case.rang or ''} {case.maladie} | ZS {(case.zs or '?').upper()}",
        f"Déplacements du cas dans l'ordre chronologique • vue {mode} • fonctionne hors ligne")]
    out.append('<style>.halo text{paint-order:stroke;stroke:#fff;stroke-width:4px;stroke-linejoin:round}</style>')
    out.append(K.card(16, 66, 848, 616))
    if kmpx:
        # échelle graphique
        km = _nice(kmpx * 120)
        px_len = km / kmpx
        out.append(f'<g transform="translate(40,650)"><rect width="{px_len:.0f}" height="5" fill="{theme.NAVY}"/>'
                   f'<text y="-5" font-size="9.5" fill="{theme.MUTED}">{km:g} km</text></g>')
        out.append(f'<text x="836" y="98" text-anchor="end" font-size="16" font-weight="800" fill="{theme.MUTED}">N ↑</text>')

    places = {_norm(p.nom): p for p in case.places}
    pair_count: Dict[Tuple[str, str], int] = {}
    arrows, badges = [], []
    for leg in legs:
        a, b = _canon(leg.src, order), _canon(leg.dst, order)
        if a not in pos or b not in pos:
            continue
        (x1, y1), (x2, y2) = pos[a], pos[b]
        key = tuple(sorted((a, b)))
        k = pair_count.get(key, 0)
        pair_count[key] = k + 1
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist
        bend = (40 + 34 * k) * (1 if (a, b) == key else -1)
        mx, my = (x1 + x2) / 2 - uy * bend, (y1 + y2) / 2 + ux * bend
        sx, sy = x1 + ux * 34, y1 + uy * 34
        ex, ey = x2 - ux * 38, y2 - uy * 38
        risk = rules.event_risk(leg.ev, case)
        col = theme.RED if leg.corps else theme.risk_color(risk)
        mk = "red" if leg.corps else K.risk_marker(risk)
        dash = ' stroke-dasharray="7 5"' if leg.corps else ""
        arrows.append(f'<path d="M{sx:.1f},{sy:.1f} Q{mx:.1f},{my:.1f} {ex:.1f},{ey:.1f}" fill="none" stroke="{col}" '
                      f'stroke-width="3" stroke-linecap="round"{dash} marker-end="url(#arr-{mk})">'
                      f'<title>{leg.n}. {K.esc(date_label(leg.ev))} {K.esc(a)} → {K.esc(b)}</title></path>')
        bx, by = 0.25 * sx + 0.5 * mx + 0.25 * ex, 0.25 * sy + 0.5 * my + 0.25 * ey
        badges.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="11" fill="#fff" stroke="{col}" stroke-width="2.2"/>'
                      f'<text x="{bx:.1f}" y="{by + 4:.1f}" text-anchor="middle" font-size="11" font-weight="800" '
                      f'fill="{col}">{leg.n}</text>')
    nodes = []
    first_visit = {}
    for leg in legs:
        first_visit.setdefault(_canon(leg.src, order), leg.ev)
        first_visit.setdefault(_canon(leg.dst, order), leg.ev)
    for o in order:
        if o not in pos:
            continue
        x, y = pos[o]
        p = places.get(_norm(o))
        risk = rules.suggest_place_risk(p, case) if p else _place_risk_from_events(o, case)
        col = theme.risk_color(risk)
        icon = PLACE_ICON.get(p.type if p else "", "pin")
        nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="30" fill="{col}" stroke="#fff" stroke-width="3.5" filter="url(#sh)"/>'
                     + icon_group(icon, x, y, 26, "#fff", 2))
        lines = K.wrap(o, 20, 2)
        nodes.append('<g class="halo">' + K.multiline(x, y + 48, lines, 12, 800, theme.TEXT)
                     + K.multiline(x, y + 48 + 15 * len(lines), [risk], 9.5, 700, col) + '</g>')
    out += arrows + nodes + badges

    # Liste des étapes
    x0 = 876
    out.append(K.card(x0, 66, 388, 616))
    out.append(K.pill(x0 + 12, 78, "Étapes du parcours"))
    y = 116
    max_rows = 13
    for leg in legs[:max_rows]:
        risk = rules.event_risk(leg.ev, case)
        col = theme.RED if leg.corps else theme.risk_color(risk)
        a, b = _canon(leg.src, order), _canon(leg.dst, order)
        out.append(f'<circle cx="{x0 + 24}" cy="{y + 5}" r="10" fill="{col}"/>'
                   f'<text x="{x0 + 24}" y="{y + 9}" text-anchor="middle" font-size="10" font-weight="800" fill="#fff">{leg.n}</text>')
        out.append(f'<text x="{x0 + 42}" y="{y + 2}" font-size="10" font-weight="800" fill="{col}">{K.esc(date_label(leg.ev))}'
                   f'<tspan fill="{theme.TEXT}"> {K.esc(a)} → {K.esc(b)}</tspan></text>')
        detail = leg.ev.titre or leg.ev.type
        if leg.ev.transport:
            detail += f" • {leg.ev.transport}"
        if leg.corps:
            detail += " • transport du corps"
        out.append(f'<text x="{x0 + 42}" y="{y + 16}" font-size="9.5" fill="{theme.MUTED}">{K.esc(detail[:62])}</text>')
        y += 40
    if len(legs) > max_rows:
        out.append(f'<text x="{x0 + 42}" y="{y}" font-size="9.5" fill="{theme.MUTED}">… {len(legs) - max_rows} autre(s) étape(s)</text>')
    if not legs:
        out.append(f'<text x="{x0 + 20}" y="{y}" font-size="11" fill="{theme.MUTED}">Aucun déplacement documenté.</text>')
    ly = 632
    out.append(K.legend_item(x0 + 14, ly, theme.ORANGE, "Déplacement du cas", "line"))
    out.append(K.legend_item(x0 + 190, ly, theme.RED, "Transport du corps", "line", dashed=True))
    out.append(K.legend_item(x0 + 14, ly + 22, theme.MUTED, "Couleur = niveau de risque", "circle"))
    out.append(K.footer("Les étapes laboratoire / investigation / riposte ne sont pas des déplacements du cas et ne figurent pas sur la carte. "
                        + ("Ajoutez la latitude/longitude des lieux pour une carte géographique." if not kmpx else "")))
    out.append("</svg>")
    return "".join(out)


def _place_risk_from_events(name: str, case: Case) -> str:
    best = "Inconnu"
    for ev in case.events:
        if _norm(name) in (_norm(ev.lieu), _norm(ev.lieu_arrivee)):
            r = rules.event_risk(ev, case)
            if theme.risk_rank(r) > theme.risk_rank(best):
                best = r
    return best


def _nice(x: float) -> float:
    if x <= 0:
        return 1
    e = 10 ** math.floor(math.log10(x))
    for m in (1, 2, 5, 10):
        if m * e >= x:
            return m * e
    return 10 * e


def render_html(case: Case) -> str:
    return render_svg_page(render_svg(case), "Carte du parcours")
