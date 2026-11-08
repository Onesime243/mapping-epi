"""Réseau de transmission / contacts : le cas au centre, les lieux d'exposition
en anneau (dans l'ordre chronologique de visite), les catégories de contacts
rattachées à leur lieu. Taille des nœuds ∝ nombre de contacts ; « ? » en pointillés."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List

from config import theme
from core import rules
from core.models import Case
from core.lieux import case_label, cle
from render import svgkit as K
from render.html_renderer import render_svg_page
from render.icons import icon_group

PLACE_ICON = {"Ménage": "home", "Village / quartier": "home", "Centre de santé": "clinic", "Hôpital": "hospital",
              "Église / lieu de culte": "church", "Funérailles": "people", "Enterrement": "grave",
              "Laboratoire": "lab", "Transport": "moto", "Marché": "people", "École": "people"}


def _norm(s: str) -> str:
    return cle(s) or " ".join((s or "").lower().split())


def _place_order(case: Case) -> List[str]:
    order: List[str] = []
    names = {_norm(p.nom): p.nom for p in case.places}
    for ev in case.sorted_events():
        for loc in (ev.lieu, ev.lieu_arrivee):
            n = _norm(loc)
            for key, real in names.items():
                if key and n and (key == n or key in n or n in key) and real not in order:
                    order.append(real)
    for p in case.places:
        if p.nom not in order:
            order.append(p.nom)
    return order


def _match_place(lieu: str, order: List[str]) -> str | None:
    n = _norm(lieu)
    if not n:
        return None
    for name in order:
        if _norm(name) == n:
            return name
    for name in order:
        k = _norm(name)
        if k and (k in n or n in k):
            return name
    return None


@dataclass
class _Node:
    kind: str          # place | group
    x: float
    y: float
    r: float
    ax: float          # point d'ancrage (position souhaitée)
    ay: float
    obj: object = None
    parent: object = None
    angle: float = 0.0


def _relax(nodes: List["_Node"], center, bounds, iters: int = 160):
    """Écarte les nœuds qui se chevauchent (marge pour les étiquettes) tout en les gardant près de leur ancre."""
    x0, y0, x1, y1 = bounds
    cx, cy, cr = center
    for _ in range(iters):
        moved = False
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx, dy = b.x - a.x, b.y - a.y
                d = math.hypot(dx, dy) or 0.01
                need = a.r + b.r + 34
                if d < need:
                    push = (need - d) / 2
                    ux, uy = dx / d, dy / d
                    a.x -= ux * push; a.y -= uy * push
                    b.x += ux * push; b.y += uy * push
                    moved = True
            dx, dy = a.x - cx, a.y - cy
            d = math.hypot(dx, dy) or 0.01
            if d < cr + a.r + 40:
                k = (cr + a.r + 40 - d)
                a.x += dx / d * k; a.y += dy / d * k
        for a in nodes:
            a.x += (a.ax - a.x) * 0.04
            a.y += (a.ay - a.y) * 0.04
            a.x = min(max(a.x, x0 + a.r + 6), x1 - a.r - 6)
            a.y = min(max(a.y, y0 + a.r + 6), y1 - a.r - 22)
        if not moved:
            break


def render_svg(case: Case) -> str:
    cx, cy = 560, 372
    bounds = (24, 74, 1096, 676)
    out = [K.svg_open(), K.header(
        f"RÉSEAU DE TRANSMISSION ET DE CONTACTS – {case_label(case).upper()} {case.maladie} | ZS {(case.zs or '?').upper()}",
        "Cas index au centre • lieux d'exposition dans l'ordre du parcours • catégories de contacts à identifier / suivre")]
    out.append('<style>.halo text{paint-order:stroke;stroke:#fff;stroke-width:3.5px;stroke-linejoin:round}</style>')
    out.append(K.card(16, 66, 1088, 616))

    order = _place_order(case)
    places = {p.nom: p for p in case.places}
    n = max(1, len(order))
    rxp, ryp = 330, 205
    nodes: List[_Node] = []
    pnode: Dict[str, _Node] = {}
    for i, name in enumerate(order):
        a = -math.pi / 2 + 2 * math.pi * i / n
        x, y = cx + rxp * math.cos(a), cy + ryp * math.sin(a)
        nd = _Node("place", x, y, 27, x, y, places.get(name), name, a)
        nodes.append(nd)
        pnode[name] = nd
    by_place: Dict[str, list] = {}
    orphans = []
    for g in case.contacts:
        t = _match_place(g.lieu, order)
        (by_place.setdefault(t, []) if t else orphans).append(g)
    for name, gs in by_place.items():
        pn = pnode[name]
        for j, g in enumerate(gs):
            spread = 0.55 * (len(gs) - 1)
            ga = pn.angle + (0 if len(gs) == 1 else -spread / 2 + spread * j / (len(gs) - 1))
            r = _group_radius(g)
            x, y = pn.x + (pn.r + r + 70) * math.cos(ga), pn.y + (pn.r + r + 70) * math.sin(ga)
            nodes.append(_Node("group", x, y, r, x, y, g, pn, ga))
    for k, g in enumerate(orphans):
        ga = math.pi / 2 + (k - (len(orphans) - 1) / 2) * 0.5
        r = _group_radius(g)
        x, y = cx + 150 * math.cos(ga), cy + 150 * math.sin(ga)
        nodes.append(_Node("group", x, y, r, x, y, g, None, ga))
    _relax(nodes, (cx, cy, 46), bounds)

    edges, shapes = [], []
    placer = K.LabelPlacer(bounds)
    placer.circle(cx, cy, 48)
    for nd in nodes:
        placer.circle(nd.x, nd.y, nd.r + 2)
    for nd in nodes:
        if nd.kind != "place":
            continue
        p = nd.obj
        risk = rules.suggest_place_risk(p, case) if p else "Inconnu"
        col = theme.risk_color(risk)
        width = 1.5 + theme.risk_rank(risk) * 1.1
        edges.append(f'<line x1="{cx}" y1="{cy}" x2="{nd.x:.1f}" y2="{nd.y:.1f}" stroke="{col}" stroke-width="{width:.1f}" '
                     f'stroke-opacity=".75"/>')
        icon = PLACE_ICON.get(p.type if p else "", "pin")
        shapes.append(f'<circle cx="{nd.x:.1f}" cy="{nd.y:.1f}" r="{nd.r}" fill="{col}" stroke="#fff" stroke-width="3" '
                      f'filter="url(#sh)"><title>{K.esc(nd.parent)} : {K.esc(risk)}</title></circle>'
                      + icon_group(icon, nd.x, nd.y, 24, "#fff", 2))
    for nd in nodes:
        if nd.kind == "group":
            px, py = (nd.parent.x, nd.parent.y) if nd.parent else (cx, cy)
            shapes.append(_group_shape(nd.obj, nd.x, nd.y, nd.r, px, py, edges))
    labels = []
    for nd in nodes:                        # étiquettes : lieux puis groupes, orientées vers l'extérieur
        dx, dy = nd.x - cx, nd.y - cy
        if abs(dy) >= abs(dx) * 0.7:
            prefer = ["below", "below-right", "below-left"] if dy > 0 else ["above", "above-right", "above-left"]
        else:
            prefer = ["right", "below-right", "above-right"] if dx > 0 else ["left", "below-left", "above-left"]
        if nd.kind == "place":
            p = nd.obj
            lines = [(ln, 11, 800, theme.INK) for ln in K.wrap_px(nd.parent, 170, 11, 800, 2)]
            if p and p.population:
                lines.append((K.ellipsize(p.population, 170, 9, 500), 9, 500, "#3A4654"))
        else:
            lines = [(ln, 10, 700, theme.INK) for ln in K.wrap_px(nd.obj.categorie, 150, 10, 700, 2)]
        labels.append(placer.place(nd.x, nd.y, nd.r + 1, lines, prefer=prefer, gap=5))

    grisk, _ = rules.global_risk(case)
    lab = K.ellipsize((case.code_cas.strip() or (f"Cas {case.rang}" if case.rang else "Cas index")).upper(), 80, 10.5, 800)
    center = (f'<circle cx="{cx}" cy="{cy}" r="44" fill="{theme.NAVY}" stroke="{theme.risk_color(grisk)}" stroke-width="6" '
              f'filter="url(#sh)"/>' + icon_group("user", cx, cy - 10, 26, "#fff", 2.2)
              + f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" fill="#fff" font-size="10.5" font-weight="800">'
                f'{K.esc(lab)}</text>'
              + f'<text x="{cx}" y="{cy + 30}" text-anchor="middle" fill="#fff" fill-opacity=".85" font-size="8.5">'
                f'{K.esc(case.sexe)} • {K.esc(case.age if case.age is not None else "?")} {K.esc(case.age_unite)}</text>')
    out += edges + shapes + [center] + ['<g class="halo">'] + labels + ['</g>']

    # panneau latéral
    s = rules.contact_summary(case)
    x0 = 1116
    out.append(K.card(x0, 66, 148, 616))
    out.append(K.pill(x0 + 10, 78, "Synthèse"))
    stats = [("Contacts listés", str(s.total_connu)), ("À haut risque", str(s.haut_risque_connu)),
             ("Catégories « ? »", str(s.categories_inconnues)),
             ("Suivis", f"{s.suivis}" + (f" ({s.pct_suivi:.0f} %)" if s.pct_suivi is not None else "")),
             ("Lieux d'exposition", str(len(case.places)))]
    y = 118
    for lab_, val in stats:
        out.append(f'<text x="{x0 + 14}" y="{y}" font-size="9.5" fill="#3A4654">{K.esc(lab_)}</text>')
        out.append(f'<text x="{x0 + 14}" y="{y + 24}" font-size="22" font-weight="800" fill="{theme.NAVY}">{K.esc(val)}</text>')
        y += 52
    out.append(K.pill(x0 + 10, y + 4, "Légende"))
    y += 42
    for col, txt in [(theme.RED, "Très élevé / très haut"), (theme.ORANGE, "Élevé / haut"),
                     (theme.YELLOW, "Modéré"), (theme.GREEN, "Contrôlé / faible"), (theme.BLUE, "Inconnu")]:
        out.append(K.legend_item(x0 + 12, y, col, K.ellipsize(txt, 100, 10), "circle"))
        y += 22
    out.append(K.legend_item(x0 + 12, y, theme.MUTED, "Nombre inconnu", "circle", dashed=True))
    y += 22
    out.append(f'<text x="{x0 + 14}" y="{y + 8}" font-size="9" fill="{theme.MUTED}">'
               f'<tspan x="{x0 + 14}">Taille ∝ nombre</tspan><tspan x="{x0 + 14}" dy="12">de contacts</tspan></text>')
    out.append(K.footer(s.phrase))
    out.append("</svg>")
    return "".join(out)


def _group_radius(g) -> float:
    return 17 if g.nombre is None else min(36, 13 + 4.0 * math.sqrt(max(g.nombre, 0)))


def _group_shape(g, gx, gy, r, px, py, edges) -> str:
    col = theme.CONTACT_RISKS.get(g.risque, theme.BLUE)
    unknown = g.nombre is None
    dash = ' stroke-dasharray="4 4"' if unknown else ""
    edges.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{gx:.1f}" y2="{gy:.1f}" stroke="{col}" stroke-width="1.6" '
                 f'stroke-opacity=".6"{dash}/>')
    txt = "?" if unknown else str(g.nombre)
    if unknown:
        node = (f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{r:.1f}" fill="#fff" stroke="{col}" stroke-width="2.4" '
                f'stroke-dasharray="4 3"/>')
        tcol = col
    else:
        fill = theme.soft(col)
        node = f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{col}" stroke-width="2" filter="url(#sh)"/>'
        tcol = theme.ink_on(fill)
    node += (f'<text x="{gx:.1f}" y="{gy + 4.5:.1f}" text-anchor="middle" font-size="{13 if r < 24 else 15}" '
             f'font-weight="800" fill="{tcol}">{txt}</text>')
    return f'<g><title>{K.esc(g.categorie)} : {txt} ({K.esc(g.risque)})</title>{node}</g>'


def render_html(case: Case) -> str:
    return render_svg_page(render_svg(case), "Réseau de transmission")
