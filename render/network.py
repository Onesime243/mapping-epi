"""Réseau de transmission / contacts : le cas au centre, les lieux d'exposition
en anneau (dans l'ordre chronologique de visite), les catégories de contacts
rattachées à leur lieu. Taille des nœuds ∝ nombre de contacts ; « ? » en pointillés."""
from __future__ import annotations

import math
from typing import Dict, List

from config import theme
from core import rules
from core.models import Case
from render import svgkit as K
from render.html_renderer import render_svg_page
from render.icons import icon_group

PLACE_ICON = {"Ménage": "home", "Village / quartier": "home", "Centre de santé": "clinic", "Hôpital": "hospital",
              "Église / lieu de culte": "church", "Funérailles": "people", "Enterrement": "grave",
              "Laboratoire": "lab", "Transport": "moto", "Marché": "people", "École": "people"}


def _norm(s: str) -> str:
    return " ".join(s.lower().replace("/", " ").split())


def _place_order(case: Case) -> List[str]:
    order: List[str] = []
    names = {_norm(p.nom): p.nom for p in case.places}
    for ev in case.events:
        for loc in (ev.lieu, ev.lieu_arrivee):
            n = _norm(loc)
            for key, real in names.items():
                if key and (key == n or key in n) and real not in order:
                    order.append(real)
    for p in case.places:
        if p.nom not in order:
            order.append(p.nom)
    return order


def render_svg(case: Case) -> str:
    cx, cy = 560, 380
    rxp, ryp = 235, 160   # anneau des lieux (ellipse)
    rxg, ryg = 430, 236   # anneau des contacts
    out = [K.svg_open(), K.header(
        f"RÉSEAU DE TRANSMISSION ET DE CONTACTS – CAS {case.rang or ''} {case.maladie} | ZS {(case.zs or '?').upper()}",
        "Cas index au centre • lieux d'exposition dans l'ordre du parcours • catégories de contacts à identifier / suivre")]
    out.append('<style>.halo text{paint-order:stroke;stroke:#fff;stroke-width:3.5px;stroke-linejoin:round}</style>')
    out.append(K.card(16, 66, 1088, 616))

    order = _place_order(case)
    places = {p.nom: p for p in case.places}
    n = max(1, len(order))
    angle: Dict[str, float] = {name: -math.pi / 2 + 2 * math.pi * i / n for i, name in enumerate(order)}

    groups_by_place: Dict[str, list] = {name: [] for name in order}
    orphans = []
    for g in case.contacts:
        target = None
        for name in order:
            if g.lieu and (_norm(g.lieu) == _norm(name)):
                target = name
        if target is None:
            for name in order:
                if g.lieu and _norm(name) in _norm(g.lieu):
                    target = name
        (groups_by_place[target] if target else orphans).append(g)

    edges, nodes, labels = [], [], []
    # cas -> lieux
    for name in order:
        a = angle[name]
        px, py = cx + rxp * math.cos(a), cy + ryp * math.sin(a)
        p = places.get(name)
        risk = rules.suggest_place_risk(p, case) if p else "Inconnu"
        col = theme.risk_color(risk)
        width = 1.5 + theme.risk_rank(risk) * 1.1
        edges.append(f'<line x1="{cx}" y1="{cy}" x2="{px:.1f}" y2="{py:.1f}" stroke="{col}" stroke-width="{width:.1f}" '
                     f'stroke-opacity=".75"/>')
        # catégories de contacts
        gs = groups_by_place.get(name, [])
        sector = 2 * math.pi / n
        for j, g in enumerate(gs):
            spread = min(sector * 0.8, 0.42 * max(1, len(gs) - 1))
            ga = a + (0 if len(gs) == 1 else -spread / 2 + spread * j / (len(gs) - 1))
            gx, gy = cx + rxg * math.cos(ga), cy + ryg * math.sin(ga)
            nodes.append(_group_node(g, gx, gy, ga, px, py, edges, labels))
        icon = PLACE_ICON.get(p.type if p else "", "pin")
        nodes.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="27" fill="{col}" stroke="#fff" stroke-width="3" filter="url(#sh)">'
                     f'<title>{K.esc(name)} — {K.esc(risk)}</title></circle>' + icon_group(icon, px, py, 24, "#fff", 2))
        lx, ly = px, py + 40
        labels.append(K.multiline(lx, ly, K.wrap(name, 18, 2), 11, 800, theme.TEXT)
                      + K.multiline(lx, ly + (14 if len(K.wrap(name, 18, 2)) == 1 else 27),
                                    K.wrap(p.population if p and p.population else "", 24, 1), 9, 500, theme.MUTED))
    for k, g in enumerate(orphans):
        ga = math.pi / 2 + (k - (len(orphans) - 1) / 2) * 0.35
        gx, gy = cx + (rxg - 60) * math.cos(ga), cy + (ryg - 30) * math.sin(ga)
        nodes.append(_group_node(g, gx, gy, ga, cx, cy, edges, labels))

    # nœud central
    grisk, _ = rules.global_risk(case)
    center = (f'<circle cx="{cx}" cy="{cy}" r="44" fill="{theme.NAVY}" stroke="{theme.risk_color(grisk)}" stroke-width="6" '
              f'filter="url(#sh)"/>' + icon_group("user", cx, cy - 10, 26, "#fff", 2.2)
              + f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" fill="#fff" font-size="11" font-weight="800">'
                f'CAS {case.rang or "?"}</text>'
              + f'<text x="{cx}" y="{cy + 30}" text-anchor="middle" fill="#fff" fill-opacity=".8" font-size="8.5">'
                f'{K.esc(case.sexe)} • {K.esc(case.age if case.age is not None else "?")} {K.esc(case.age_unite)}</text>')
    out += edges + nodes + [center] + ['<g class="halo">'] + labels + ['</g>']

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
    for lab, val in stats:
        out.append(f'<text x="{x0 + 14}" y="{y}" font-size="9.5" fill="{theme.MUTED}">{K.esc(lab)}</text>')
        out.append(f'<text x="{x0 + 14}" y="{y + 24}" font-size="22" font-weight="800" fill="{theme.NAVY}">{K.esc(val)}</text>')
        y += 52
    out.append(K.pill(x0 + 10, y + 4, "Légende"))
    y += 42
    for col, txt in [(theme.RED, "Très élevé / très haut"), (theme.ORANGE, "Élevé / haut"),
                     (theme.GREEN, "Modéré / contrôlé"), (theme.BLUE, "Inconnu")]:
        out.append(K.legend_item(x0 + 12, y, col, txt, "circle"))
        y += 22
    out.append(K.legend_item(x0 + 12, y, theme.MUTED, "Nombre inconnu", "circle", dashed=True))
    y += 22
    out.append(f'<text x="{x0 + 14}" y="{y + 8}" font-size="9" fill="{theme.MUTED}">'
               f'<tspan x="{x0 + 14}">Taille ∝ nombre</tspan><tspan x="{x0 + 14}" dy="12">de contacts</tspan></text>')
    out.append(K.footer(s.phrase))
    out.append("</svg>")
    return "".join(out)


def _group_node(g, gx, gy, ga, px, py, edges, labels) -> str:
    col = theme.CONTACT_RISKS.get(g.risque, theme.BLUE)
    unknown = g.nombre is None
    r = 17 if unknown else min(40, 13 + 4.2 * math.sqrt(max(g.nombre, 0)))
    dash = ' stroke-dasharray="4 4"' if unknown else ""
    edges.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{gx:.1f}" y2="{gy:.1f}" stroke="{col}" stroke-width="1.6" '
                 f'stroke-opacity=".55"{dash}/>')
    txt = "?" if unknown else str(g.nombre)
    if unknown:
        node = (f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{r:.1f}" fill="#fff" stroke="{col}" stroke-width="2.4" '
                f'stroke-dasharray="4 3"/>')
        tcol = col
    else:
        node = f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{r:.1f}" fill="{col}" stroke="#fff" stroke-width="2" filter="url(#sh)"/>'
        tcol = "#fff"
    node += (f'<text x="{gx:.1f}" y="{gy + 4.5:.1f}" text-anchor="middle" font-size="{13 if r < 24 else 15}" '
             f'font-weight="800" fill="{tcol}">{txt}</text>')
    node = f'<g><title>{K.esc(g.categorie)} : {txt} ({K.esc(g.risque)})</title>{node}</g>'
    lx, ly = gx + (r + 8) * math.cos(ga), gy + (r + 8) * math.sin(ga)
    anchor = "start" if math.cos(ga) > 0.25 else ("end" if math.cos(ga) < -0.25 else "middle")
    if anchor == "middle":
        ly += 6 if math.sin(ga) > 0 else -2
    lines = K.wrap(g.categorie, 20, 2)
    if math.sin(ga) < -0.3 and anchor == "middle":
        ly -= 12 * (len(lines) - 1)
    labels.append(K.multiline(lx, ly + 3, lines, 10, 700, theme.TEXT, anchor))
    return node


def render_html(case: Case) -> str:
    return render_svg_page(render_svg(case), "Réseau de transmission")
