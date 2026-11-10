"""Chaînes de transmission : arbres « cas source → cas secondaires », par génération.

Le lien vient du champ « ID du cas source » de chaque fiche (comparé à l'ID des autres fiches).
Les cas sont placés en colonnes (génération 1, 2, 3…), reliés par une flèche dont le trait suit le
statut de contact : plein = contact connu suivi, tirets = contact connu, pointillés = autre.
L'étiquette « +n j » donne l'intervalle entre les J0 rapportés (intervalle sériel).
"""
from __future__ import annotations

from statistics import mean
from typing import Dict, List, Optional, Tuple

from config import theme
from core import links, rules
from core.models import Case
from render import svgkit as K
from render.html_renderer import render_svg_page

AREA = (16, 66, 860, 616)            # x, y, w, h de la zone des chaînes
PANEL_X = 888
LIEN_STYLE = {"Contact connu suivi": ("", theme.NAVY, 2.6, "navy"), "Contact connu": ("7 4", theme.ORANGE, 2.2, "orange"),
              "Autre": ("2 4", theme.MUTED, 2.0, "muted")}
LIEN_LEGENDE = {"Contact connu suivi": "Contact connu suivi", "Contact connu": "Contact connu (non suivi)",
                "Autre": "Statut de contact non précisé"}


def _component(root: links.Node) -> List[links.Node]:
    out, stack = [], [root]
    while stack:
        n = stack.pop()
        out.append(n)
        stack.extend(n.children)
    return out


def _leaves(n: links.Node) -> int:
    return 1 if not n.children else sum(_leaves(c) for c in n.children)


def render_svg(cases: List[Case], focus: Optional[Case] = None, zone: str = "") -> str:
    ch = links.build_chains(cases)
    roots = ch.roots
    if focus:
        mine = [r for r in roots if any(n.key == focus.id for n in _component(r))]
        if mine:
            roots = mine
    title = "CHAÎNES DE TRANSMISSION" + (f" | {zone.upper()}" if zone else "")
    out = [K.svg_open(), K.header(title, "Cas source → cas secondaires, par génération • trait : statut de contact • "
                                         "+n j : jours entre les J0 rapportés")]
    out.append('<style>.halo text{paint-order:stroke;stroke:#fff;stroke-width:3.5px;stroke-linejoin:round}</style>')
    x0, y0, aw, ah = AREA
    out.append(K.card(x0, y0, aw, ah))

    # --- disposition : une ligne par feuille, colonnes par génération
    max_rows = 22
    rows_needed, shown, hidden = 0, [], 0
    for r in roots:
        lv = _leaves(r)
        if rows_needed + lv <= max_rows or not shown:
            shown.append(r)
            rows_needed += lv
        else:
            hidden += 1
    max_gen = max((n.gen for r in shown for n in _component(r)), default=0)
    top, bottom = y0 + 46, y0 + ah - 46
    gap_chain = 10
    row_h = min(64.0, (bottom - top - gap_chain * max(0, len(shown) - 1)) / max(1, rows_needed))
    node_h = max(24.0, min(44.0, row_h - 8))
    col_w = min(230.0, (aw - 40) / (max_gen + 1))
    node_w = min(168.0, col_w - 44)
    small = node_h < 34

    pos: Dict[str, Tuple[float, float]] = {}
    cursor = [top]

    def place(n: links.Node) -> float:
        if not n.children:
            y = cursor[0] + row_h / 2
            cursor[0] += row_h
        else:
            ys = [place(c) for c in n.children]
            y = (ys[0] + ys[-1]) / 2
        pos[n.key] = (x0 + 20 + n.gen * col_w, y)
        return y

    for r in shown:
        place(r)
        cursor[0] += gap_chain

    if shown:
        for gidx in range(max_gen + 1):
            gx = x0 + 20 + gidx * col_w + node_w / 2
            lbl = "Source / 1re génération" if gidx == 0 else f"Génération {gidx + 1}"
            out.append(f'<text x="{gx:.1f}" y="{y0 + 26}" text-anchor="middle" font-size="10" font-weight="800" '
                       f'fill="{theme.MUTED}" letter-spacing=".6">{K.esc(lbl.upper())}</text>')
            if gidx:
                lx = x0 + 20 + gidx * col_w - (col_w - node_w) / 2
                out.append(f'<line x1="{lx:.1f}" y1="{y0 + 36}" x2="{lx:.1f}" y2="{y0 + ah - 40}" stroke="{theme.BORDER}" '
                           'stroke-dasharray="3 5"/>')

    # --- liens
    for r in shown:
        for n in _component(r):
            px, py = pos[n.key]
            for c in n.children:
                cx, cy = pos[c.key]
                dash, col, sw, mk = LIEN_STYLE.get(c.lien, LIEN_STYLE["Autre"])
                x1, x2 = px + node_w, cx - 4
                mx = (x1 + x2) / 2
                da = f' stroke-dasharray="{dash}"' if dash else ""
                out.append(f'<path d="M{x1:.1f} {py:.1f} C{mx:.1f} {py:.1f} {mx:.1f} {cy:.1f} {x2:.1f} {cy:.1f}" fill="none" '
                           f'stroke="{col}" stroke-width="{sw}"{da} marker-end="url(#arr-{mk})"><title>{K.esc(c.lien)}</title></path>')
                si = links.serial_interval(n.case, c.case)
                if si is not None:
                    out.append(f'<g class="halo"><text x="{mx:.1f}" y="{(py + cy) / 2 - 4:.1f}" text-anchor="middle" '
                               f'font-size="9.5" font-weight="800" fill="{col}">{si:+d} j</text></g>')

    # --- nœuds
    for r in shown:
        for n in _component(r):
            x, y = pos[n.key]
            yt = y - node_h / 2
            if n.case is None:
                out.append(f'<rect x="{x:.1f}" y="{yt:.1f}" width="{node_w:.1f}" height="{node_h:.1f}" rx="8" fill="#fff" '
                           f'stroke="{theme.MUTED}" stroke-width="1.6" stroke-dasharray="4 3"/>')
                lines = K.wrap("Source hors périmètre : " + n.label, int(node_w / 6.2), 1 if small else 2)
                out.append(K.multiline(x + node_w / 2, y + (3 if len(lines) == 1 else -3), lines, 9.5, 700, theme.MUTED))
                continue
            c = n.case
            risk, _ = rules.global_risk(c)
            edge = theme.RED if c.issue == "Décès" else theme.risk_color(risk)
            is_focus = focus is not None and c.id == focus.id
            if is_focus:
                out.append(f'<rect x="{x - 4:.1f}" y="{yt - 4:.1f}" width="{node_w + 8:.1f}" height="{node_h + 8:.1f}" '
                           f'rx="11" fill="none" stroke="{theme.TEAL}" stroke-width="2.5"/>')
            out.append(f'<rect x="{x:.1f}" y="{yt:.1f}" width="{node_w:.1f}" height="{node_h:.1f}" rx="8" fill="{theme.NAVY}" '
                       f'filter="url(#sh)"/><rect x="{x:.1f}" y="{yt:.1f}" width="6" height="{node_h:.1f}" rx="3" fill="{edge}"/>')
            l1 = K.ellipsize(links.case_label(c), node_w - 22, 11.5, 800)
            j0 = f"J0 {c.debut_symptomes:%d/%m}" if c.debut_symptomes else "J0 ?"
            l2 = K.ellipsize(f"{c.zs or 'ZS ?'} / {c.aire_sante or 'AS ?'} • {j0}", node_w - 20, 9.5)
            tip = f"{l1} : {c.maladie} {c.statut}, issue {c.issue}"
            if small:
                out.append(f'<text x="{x + 12:.1f}" y="{y + 4:.1f}" font-size="10.5" font-weight="800" fill="#fff">'
                           f'{K.esc(l1)}<title>{K.esc(tip + ", " + l2)}</title></text>')
            else:
                out.append(f'<text x="{x + 12:.1f}" y="{y - 3:.1f}" font-size="11.5" font-weight="800" fill="#fff">'
                           f'{K.esc(l1)}<title>{K.esc(tip)}</title></text>')
                out.append(f'<text x="{x + 12:.1f}" y="{y + 12:.1f}" font-size="9.5" fill="#fff" fill-opacity=".82">'
                           f'{K.esc(l2)}</text>')
            if c.issue == "Décès":
                out.append(f'<text x="{x + node_w - 8:.1f}" y="{yt + 13:.1f}" text-anchor="end" font-size="10" '
                           f'font-weight="800" fill="#FF9C8F">†</text>')

    if not shown:
        msg = ["Aucun lien de transmission saisi.",
               "Dans chaque fiche (onglet Identité), renseignez « ID du cas source » :",
               "l'ID (N° EPID) du cas dont ce cas est le contact."]
        out.append(K.multiline(x0 + aw / 2, y0 + ah / 2 - 20, msg, 13, 600, theme.MUTED, lh=1.6))
    if hidden:
        out.append(f'<text x="{x0 + aw - 16}" y="{y0 + ah - 14}" text-anchor="end" font-size="10" fill="{theme.RED}" '
                   f'font-weight="700">+ {hidden} autre(s) chaîne(s) non affichée(s) : filtrez par province / zone.</text>')

    # --- légende
    lx, ly = x0 + 16, y0 + ah - 18
    for i, (lab, (dash, col, _sw, _mk)) in enumerate(LIEN_STYLE.items()):
        out.append(K.legend_item(lx + i * 190, ly, col, LIEN_LEGENDE[lab], kind="line", dashed=bool(dash)))
    out.append(K.legend_item(lx + 590, ly, theme.RED, "Bord : risque / décès"))

    # --- panneau de synthèse
    out.append(K.card(PANEL_X, 66, 376, 616))
    out.append(K.pill(PANEL_X + 12, 78, "Synthèse"))
    case_nodes = [n for r in ch.roots for n in _component(r) if n.case]
    sis = [si for p, cid in ch.edges
           if (si := links.serial_interval(next(x for x in cases if x.id == p), next(x for x in cases if x.id == cid))) is not None]
    longest = max((max(n.gen for n in _component(r)) + 1 for r in ch.roots), default=0)
    stats = [f"{len(cases)} cas dans le périmètre", f"{len(ch.roots)} chaîne(s) • {len(case_nodes)} cas reliés",
             f"Chaîne la plus longue : {longest} génération(s)" if longest else "Aucune chaîne",
             f"Intervalle moyen entre J0 : {mean(sis):.1f} j (n = {len(sis)})" if sis else "Intervalle entre J0 : ? (dates manquantes)"]
    y = 116
    for s in stats:
        out.append(f'<text x="{PANEL_X + 16}" y="{y}" font-size="11.5" font-weight="700" fill="{theme.TEXT}">{K.esc(s)}</text>')
        y += 19
    y += 8
    out.append(K.pill(PANEL_X + 12, y, "Cas sans lien saisi"))
    y += 36
    if not ch.isolated:
        out.append(f'<text x="{PANEL_X + 16}" y="{y}" font-size="10.5" fill="{theme.MUTED}">Tous les cas sont rattachés.</text>')
        y += 18
    for c in ch.isolated[:7]:
        j0 = f"J0 {c.debut_symptomes:%d/%m}" if c.debut_symptomes else "J0 ?"
        out.append(f'<text x="{PANEL_X + 16}" y="{y}" font-size="10.5" fill="{theme.TEXT}"><tspan font-weight="800">'
                   f'{K.esc(K.ellipsize(links.case_long_label(c), 190, 10.5, 800))}</tspan> • {K.esc(c.aire_sante or "AS ?")} • {j0}</text>')
        y += 16
    if len(ch.isolated) > 7:
        out.append(f'<text x="{PANEL_X + 16}" y="{y}" font-size="10" fill="{theme.MUTED}">… et {len(ch.isolated) - 7} autre(s)</text>')
        y += 16
    y += 10
    out.append(K.pill(PANEL_X + 12, y, "Pistes : lieux communs"))
    y += 36
    linked = set(ch.edges) | {(b, a) for a, b in ch.edges}
    pistes = []
    for sp in links.shared_places(cases, focus):
        for a, b in sp.pistes:
            if (a.id, b.id) not in linked:
                pistes.append((sp.name, a, b))
    if not pistes:
        out.append(f'<text x="{PANEL_X + 16}" y="{y}" font-size="10.5" fill="{theme.MUTED}">'
                   'Aucune piste non reliée détectée.</text>')
    for name, a, b in pistes[:6]:
        out.append(f'<text x="{PANEL_X + 16}" y="{y}" font-size="10.5" font-weight="800" fill="{theme.ORANGE}">'
                   f'{K.esc(links.case_label(a))} → {K.esc(links.case_label(b))} ?</text>')
        out.append(f'<text x="{PANEL_X + 16}" y="{y + 14}" font-size="9.5" fill="{theme.MUTED}">'
                   f'{K.esc(("à " + name)[:58])}</text>')
        y += 32
        if y > 640:
            break
    for msg in ch.ignored[:2]:
        out.append(f'<text x="{PANEL_X + 16}" y="{min(y, 650)}" font-size="9" fill="{theme.RED}">{K.esc(msg[:66])}</text>')
        y += 13
    out.append(K.footer("Lien = ID du cas source saisi dans la fiche ; une « piste » (cas contagieux et cas exposé au même lieu) "
                        "oriente l'investigation mais n'établit pas la transmission."))
    out.append("</svg>")
    return "".join(out)


def render_html(cases: List[Case], focus: Optional[Case] = None, zone: str = "") -> str:
    return render_svg_page(render_svg(cases, focus, zone), "Chaînes de transmission")
