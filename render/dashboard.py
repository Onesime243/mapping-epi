"""Tableau de bord multi-cas : relie les cas qui partagent un lieu ou un événement
(même église, mêmes funérailles, même structure de soins) pour faire apparaître
les chaînes de transmission possibles."""
from __future__ import annotations

import math
from datetime import date
from collections import defaultdict
from typing import Dict, List, Set

from config import theme
from core import rules
from core.lieux import VAGUES, _noms_du_cas as _noms, case_label, cle, frequentes
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


def _labels_cas(cs: List[Case]) -> str:
    cnt: Dict[str, int] = defaultdict(int)
    for c in cs:
        cnt[case_label(c)] += 1
    return ", ".join(f"{k} ×{v}" if v > 1 else k for k, v in cnt.items())


def render_svg(cases: List[Case], zone: str = "", titre: str = "") -> str:
    cases = sorted(cases, key=lambda c: (c.debut_symptomes or date.max, c.rang or 999))
    titre = titre or f"TABLEAU DE BORD MULTI-CAS{(' | ZS ' + zone.upper()) if zone else ''}"
    out = [K.svg_open(), K.header(titre, "Cas reliés lorsqu'ils ont fréquenté un même lieu • épaisseur ∝ nombre de lieux communs")]
    out.append('<style>.halo text{paint-order:stroke;stroke:#fff;stroke-width:4px;stroke-linejoin:round}</style>')
    out.append(K.card(16, 66, 860, 616))
    n = len(cases)
    if n == 0:
        out.append(f'<text x="446" y="380" text-anchor="middle" font-size="14" fill="{theme.MUTED}">Aucun cas enregistré.</text></svg>')
        return "".join(out)
    cx, cy = 446, 360
    rx, ry = (300, 205) if n > 1 else (0, 0)
    r = 34 if n <= 12 else (27 if n <= 20 else 21)
    pos = []
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * i / n
        pos.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    keys = [{cle(nm) for nm, _, _ in _noms(c)} - VAGUES for c in cases]
    lieux = frequentes(cases, min_cas=2)
    pair: Dict[tuple, List[str]] = defaultdict(list)
    for L in lieux:
        idx = [i for i in range(n) if L.cle in keys[i]]
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                pair[(idx[a], idx[b])].append(L.nom)
    for (a, b), names in pair.items():
        (x1, y1), (x2, y2) = pos[a], pos[b]
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{theme.ORANGE}" '
                   f'stroke-width="{1.2 + 1.3 * min(len(names), 6):.1f}" stroke-opacity=".55">'
                   f'<title>{K.esc(", ".join(names))}</title></line>')
    placer = K.LabelPlacer((24, 74, 868, 676))
    for x, y in pos:
        placer.circle(x, y, r + 5)
    nodes, labels = [], []
    for i, c in enumerate(cases):
        x, y = pos[i]
        risk, _ = rules.global_risk(c)
        col = theme.risk_color(risk)
        lab = K.ellipsize(c.code_cas.strip() or (f"Cas {c.rang}" if c.rang else "Cas ?"), 2 * r - 8, 11 if r > 25 else 9, 800)
        nodes.append(f'<g><title>{K.esc(case_label(c))} — {K.esc(c.aire_sante or "?")} — risque {K.esc(risk)}</title>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{theme.NAVY}" stroke="{col}" stroke-width="5" filter="url(#sh)"/>'
                     f'<text x="{x:.1f}" y="{y + 1:.1f}" text-anchor="middle" fill="#fff" font-size="{11 if r > 25 else 9}" '
                     f'font-weight="800">{K.esc(lab)}</text>'
                     f'<text x="{x:.1f}" y="{y + 13:.1f}" text-anchor="middle" fill="#fff" fill-opacity=".8" font-size="8">'
                     f'{K.esc(c.maladie)}</text></g>')
        sub = [(K.ellipsize(f"{c.aire_sante or '?'} • {c.sexe} {c.age if c.age is not None else '?'} {c.age_unite}", 150, 9.5, 600),
                9.5, 600, theme.INK),
               (f"J0 {c.debut_symptomes:%d/%m}" if c.debut_symptomes else "J0 ?", 9, 500, "#3A4654")]
        dx, dy = x - cx, y - cy
        prefer = (["below", "below-right", "below-left"] if dy > 0 else ["above", "above-right", "above-left"]) \
            if abs(dy) >= abs(dx) * 0.7 else (["right"] if dx > 0 else ["left"])
        labels.append(placer.place(x, y, r + 3, sub, prefer=prefer))
    out += nodes + ['<g class="halo">'] + labels + ['</g>']
    # panneau : lieux les plus fréquentés
    x0 = 888
    out.append(K.card(x0, 66, 376, 616))
    out.append(K.pill(x0 + 12, 78, "Lieux les plus fréquentés"))
    y = 122
    if not lieux:
        out.append(f'<text x="{x0 + 16}" y="{y}" font-size="11" fill="{theme.MUTED}">Aucun lieu commun entre les cas.</text>')
    shown = 0
    for L in lieux:
        if y > 640:
            break
        col = theme.risk_color(L.risque)
        out.append(f'<rect x="{x0 + 16}" y="{y - 12}" width="38" height="18" rx="4" fill="{theme.soft(col)}"/>'
                   f'<text x="{x0 + 35}" y="{y + 1}" text-anchor="middle" font-size="10" font-weight="800" '
                   f'fill="{theme.ink_on(theme.soft(col))}">{L.n_cas} cas</text>')
        out.append(f'<text x="{x0 + 62}" y="{y + 1}" font-size="11" font-weight="800" fill="{theme.INK}">'
                   f'{K.esc(K.ellipsize(L.nom, 296, 11, 800))}</text>')
        out.append(f'<text x="{x0 + 62}" y="{y + 16}" font-size="9.5" fill="#3A4654">'
                   f'{K.esc(K.ellipsize(_labels_cas(L.cas), 296, 9.5))}</text>')
        y += 38
        shown += 1
    if len(lieux) > shown:
        out.append(f'<text x="{x0 + 62}" y="{y - 6}" font-size="9.5" fill="{theme.MUTED}">… {len(lieux) - shown} autre(s) lieu(x)</text>')
    total = sum(rules.contact_summary(c).total_connu for c in cases)
    out.append(K.footer(f"{n} cas • {total} contacts dénombrés • {len(lieux)} lieu(x) fréquenté(s) par au moins 2 cas. "
                        "Un lieu commun n'établit pas un lien de transmission : il oriente l'investigation."))
    out.append("</svg>")
    return "".join(out)


def render_html(cases: List[Case], zone: str = "", titre: str = "") -> str:
    return render_svg_page(render_svg(cases, zone, titre), "Tableau de bord multi-cas")
