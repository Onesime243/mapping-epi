"""Tableau de bord multi-cas : relie les cas qui partagent un lieu ou un événement
(même église, mêmes funérailles, même structure de soins) pour faire apparaître
les chaînes de transmission possibles."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Set

from config import theme
from core import rules
from core.models import Case
from render import svgkit as K
from render.html_renderer import render_svg_page


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace("/", " ").split())


_DISPLAY: Dict[str, str] = {}


def case_places(c: Case) -> Set[str]:
    names = [p.nom for p in c.places] + [loc for e in c.events for loc in (e.lieu, e.lieu_arrivee)]
    out = set()
    for name in names:
        if name.strip():
            key = _norm(name)
            _DISPLAY.setdefault(key, name.strip())
            out.add(key)
    return out


def display(key: str) -> str:
    return _DISPLAY.get(key, key)


def shared_places(cases: List[Case]) -> Dict[str, List[int]]:
    where: Dict[str, List[int]] = defaultdict(list)
    for i, c in enumerate(cases):
        for p in case_places(c):
            where[p].append(i)
    return {p: ids for p, ids in where.items() if len(ids) > 1}


def render_svg(cases: List[Case], zone: str = "") -> str:
    cases = sorted(cases, key=lambda c: c.rang or 999)
    out = [K.svg_open(), K.header(
        f"TABLEAU DE BORD MULTI-CAS{(' | ZS ' + zone.upper()) if zone else ''}",
        "Cas reliés lorsqu'ils partagent un lieu ou un événement • épaisseur ∝ nombre de lieux communs")]
    out.append('<style>.halo text{paint-order:stroke;stroke:#fff;stroke-width:4px;stroke-linejoin:round}</style>')
    out.append(K.card(16, 66, 860, 616))
    n = len(cases)
    if n == 0:
        out.append(f'<text x="446" y="380" text-anchor="middle" font-size="14" fill="{theme.MUTED}">Aucun cas enregistré.</text></svg>')
        return "".join(out)
    cx, cy, rx, ry = 446, 372, 320, 225
    pos = []
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * i / n
        pos.append((cx, cy) if n == 1 else (cx + rx * math.cos(a), cy + ry * math.sin(a)))
    sp = shared_places(cases)
    pair: Dict[tuple, List[str]] = defaultdict(list)
    for p, ids in sp.items():
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                pair[(ids[a], ids[b])].append(p)
    for (a, b), names in pair.items():
        (x1, y1), (x2, y2) = pos[a], pos[b]
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{theme.ORANGE}" '
                   f'stroke-width="{1.5 + 1.5 * len(names):.1f}" stroke-opacity=".7"><title>{K.esc(", ".join(display(x) for x in names))}</title></line>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        out.append('<g class="halo">' + K.multiline(mx, my, K.wrap(", ".join(display(x) for x in names), 26, 2), 9, 600, theme.MUTED) + '</g>')
    for i, c in enumerate(cases):
        x, y = pos[i]
        risk, _ = rules.global_risk(c)
        col = theme.risk_color(risk)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="34" fill="{theme.NAVY}" stroke="{col}" stroke-width="6" filter="url(#sh)"/>')
        out.append(f'<text x="{x:.1f}" y="{y + 2:.1f}" text-anchor="middle" fill="#fff" font-size="13" font-weight="800">'
                   f'Cas {c.rang or "?"}</text>')
        out.append(f'<text x="{x:.1f}" y="{y + 15:.1f}" text-anchor="middle" fill="#fff" fill-opacity=".8" font-size="8.5">'
                   f'{K.esc(c.maladie)}</text>')
        sub = [f"{c.aire_sante or '?'} • {c.sexe} {c.age if c.age is not None else '?'} {c.age_unite}",
               f"J0 {c.debut_symptomes:%d/%m}" if c.debut_symptomes else "J0 ?"]
        out.append('<g class="halo">' + K.multiline(x, y + 52, sub, 9.5, 600, theme.TEXT) + '</g>')
    # panneau
    x0 = 888
    out.append(K.card(x0, 66, 376, 616))
    out.append(K.pill(x0 + 12, 78, "Lieux partagés"))
    y = 120
    if not sp:
        out.append(f'<text x="{x0 + 16}" y="{y}" font-size="11" fill="{theme.MUTED}">Aucun lieu commun entre les cas.</text>')
    for p, ids in sorted(sp.items(), key=lambda kv: -len(kv[1]))[:14]:
        out.append(f'<text x="{x0 + 16}" y="{y}" font-size="11" font-weight="800" fill="{theme.TEXT}">{K.esc(display(p)[:40])}</text>')
        out.append(f'<text x="{x0 + 16}" y="{y + 15}" font-size="9.5" fill="{theme.MUTED}">'
                   f'{K.esc(", ".join("Cas " + str(cases[i].rang or "?") for i in ids))}</text>')
        y += 38
    total = sum(rules.contact_summary(c).total_connu for c in cases)
    out.append(K.footer(f"{n} cas • {total} contacts dénombrés • {len(sp)} lieu(x) commun(s). "
                        "Un lieu commun n'établit pas un lien de transmission : il oriente l'investigation."))
    out.append("</svg>")
    return "".join(out)


def render_html(cases: List[Case], zone: str = "") -> str:
    return render_svg_page(render_svg(cases, zone), "Tableau de bord multi-cas")
