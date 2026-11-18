"""Chaînes de transmission : arbres « cas source → cas secondaires », par génération.

Le lien vient du champ « ID du cas source » de chaque fiche (comparé à l'ID des autres fiches).
Les cas sont placés en colonnes (génération 1, 2, 3…), reliés par une flèche dont le trait suit le
statut de contact : plein = contact connu suivi, tirets = contact connu, pointillés = autre.
L'étiquette « +n j » donne l'intervalle entre les J0 rapportés (intervalle sériel).

Mise en page : chaque texte est mesuré (police Inter, svgkit.text_width) et réduit, coupé en lignes ou
abrégé pour tenir dans sa case ; la légende est disposée en lignes qui ne se chevauchent pas ; le panneau
de droite avance ligne par ligne et s'arrête avant le bas du cadre.
"""
from __future__ import annotations

from statistics import mean
from typing import Dict, List, Optional, Tuple

from config import theme
from core import links, rules
from core.models import Case
from render import svgkit as K
from render.html_renderer import render_svg_page
from render.libelles import cas, cas_long, jour, tr, trf, val

AREA = (16, 66, 860, 616)            # x, y, w, h de la zone des chaînes
PANEL_X, PANEL_W = 888, 376
PANEL_TW = PANEL_W - 32               # largeur utile du texte dans le panneau
PANEL_YMAX = 66 + 616 - 12            # dernière ligne de base possible dans le panneau
LIEN_STYLE = {"Contact connu suivi": ("", theme.NAVY, 2.6, "navy"), "Contact connu": ("7 4", theme.ORANGE, 2.2, "orange"),
              "Autre": ("2 4", theme.MUTED, 2.0, "muted")}
LIEN_LEGENDE = {"Contact connu suivi": "Contact connu suivi", "Contact connu": "Contact connu (non suivi)",
                "Autre": "Statut de contact non précisé"}
MIN_ROW_H = 22.0                      # hauteur minimale d'une ligne (un cas feuille)
GAP_CHAIN = 8.0                       # espace entre deux chaînes


def _component(root: links.Node) -> List[links.Node]:
    out, stack = [], [root]
    while stack:
        n = stack.pop()
        out.append(n)
        stack.extend(n.children)
    return out


def _leaves(n: links.Node) -> int:
    return 1 if not n.children else sum(_leaves(c) for c in n.children)


def _fit(text: str, max_w: float, size: float, weight: int = 400, min_size: float = 7.0) -> Tuple[str, float]:
    """Plus grande taille (≤ size, ≥ min_size) à laquelle le texte tient sur une ligne ; abrégé « … » sinon."""
    s = size
    while s > min_size and K.text_width(text, s, weight) > max_w:
        s -= 0.5
    return K.ellipsize(text, max_w, s, weight), s


def _text(x, y, text, size, weight=400, fill=None, anchor="start") -> str:
    a = "" if anchor == "start" else f' text-anchor="{anchor}"'
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size:g}" font-weight="{weight}" fill="{fill or theme.TEXT}"{a}>'
            f'{K.esc(text)}</text>')


# ---------------------------------------------------------------------------
# Légende : éléments mesurés, disposés en lignes
# ---------------------------------------------------------------------------
def _legend_items() -> List[tuple]:
    items = [("line", col, tr(LIEN_LEGENDE[lab]), bool(dash)) for lab, (dash, col, _sw, _mk) in LIEN_STYLE.items()]
    items.append(("edge", theme.RED, tr("Bord : risque / décès"), False))
    items.append(("box", theme.MUTED, tr("Source hors périmètre"), True))
    return items


def _legend_width(item) -> float:
    return 26 + K.text_width(item[2], 10)


def legend_layout(x0: float, x1: float, gap: float = 22) -> List[List[Tuple[float, tuple]]]:
    """Lignes de légende : [(x, élément)] ; un élément qui dépasserait x1 passe à la ligne suivante."""
    lines: List[List[Tuple[float, tuple]]] = [[]]
    x = x0
    for it in _legend_items():
        w = _legend_width(it)
        if lines[-1] and x + w > x1:
            lines.append([])
            x = x0
        lines[-1].append((x, it))
        x += w + gap
    return lines


def _legend_svg(x, y, item) -> str:
    kind, col, text, dashed = item
    if kind == "line":
        return K.legend_item(x, y, col, text, kind="line", dashed=dashed)
    if kind == "box":
        sym = (f'<rect x="{x:.1f}" y="{y - 6:.1f}" width="20" height="12" rx="3" fill="#fff" stroke="{col}" '
               'stroke-width="1.4" stroke-dasharray="3 2"/>')
    else:
        sym = (f'<rect x="{x:.1f}" y="{y - 6:.1f}" width="20" height="12" rx="3" fill="{theme.NAVY}"/>'
               f'<rect x="{x:.1f}" y="{y - 6:.1f}" width="5" height="12" rx="2" fill="{col}"/>')
    return sym + f'<text x="{x + 26:.1f}" y="{y + 3.5:.1f}" font-size="10" fill="{theme.MUTED}">{K.esc(text)}</text>'


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------
def render_svg(cases: List[Case], focus: Optional[Case] = None, zone: str = "") -> str:
    ch = links.build_chains(cases)
    roots = ch.roots
    if focus:
        mine = [r for r in roots if any(n.key == focus.id for n in _component(r))]
        if mine:
            roots = mine
    title = tr("CHAÎNES DE TRANSMISSION") + (f" | {tr(zone).upper()}" if zone else "")
    out = [K.svg_open(), K.header(title, jour(tr("Cas source → cas secondaires, par génération • trait : statut de contact • "
                                                "+n j : jours entre les J0 rapportés")))]
    out.append('<style>.halo text{paint-order:stroke;stroke:#fff;stroke-width:3.5px;stroke-linejoin:round}</style>')
    x0, y0, aw, ah = AREA
    out.append(K.card(x0, y0, aw, ah))

    # --- légende (mesurée d'abord : elle fixe le bas de la zone des chaînes)
    leg_lines = legend_layout(x0 + 16, x0 + aw - 16)
    leg_lh = 18
    leg_y = y0 + ah - 18 - leg_lh * (len(leg_lines) - 1)        # ligne de base de la première ligne de légende

    # --- disposition : une ligne par feuille, colonnes par génération
    top, bottom = y0 + 46, leg_y - 24
    avail = bottom - top
    rows_needed, shown, hidden = 0, [], 0
    for r in roots:
        lv = _leaves(r)
        need = (rows_needed + lv) * MIN_ROW_H + GAP_CHAIN * len(shown)
        if need <= avail or not shown:
            shown.append(r)
            rows_needed += lv
        else:
            hidden += 1
    max_gen = max((n.gen for r in shown for n in _component(r)), default=0)
    row_h = min(64.0, (avail - GAP_CHAIN * max(0, len(shown) - 1)) / max(1, rows_needed))
    node_h = max(16.0, min(44.0, row_h - 6))
    col_w = min(230.0, (aw - 40) / (max_gen + 1))
    link_w = max(40.0, min(62.0, col_w * 0.3))                     # place de la flèche et de l'étiquette « +n j »
    node_w = min(168.0, col_w - link_w)
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
        cursor[0] += GAP_CHAIN

    if shown:
        for gidx in range(max_gen + 1):
            if gidx == 0:
                cands = [tr("Source / 1re génération"), tr("Source / G1"), tr("Source")]
            else:
                cands = [trf("Génération {n}", n=gidx + 1), trf("Gén. {n}", n=gidx + 1), f"G{gidx + 1}"]
            room = col_w - 8
            for c in cands:
                lbl, size = _fit(c.upper(), room, 10, 800, 8.0)
                if not lbl.endswith("…"):
                    break
            else:
                lbl, size = _fit(cands[-1].upper(), room, 10, 800, 6.5)
            half = K.text_width(lbl, size, 800) / 2
            gx = x0 + 20 + gidx * col_w + node_w / 2
            gx = min(max(gx, x0 + 8 + half), x0 + aw - 8 - half)
            out.append(f'<text x="{gx:.1f}" y="{y0 + 26}" text-anchor="middle" font-size="{size:g}" font-weight="800" '
                       f'fill="{theme.MUTED}">{K.esc(lbl)}</text>')
            if gidx:
                lx = x0 + 20 + gidx * col_w - (col_w - node_w) / 2
                out.append(f'<line x1="{lx:.1f}" y1="{y0 + 36}" x2="{lx:.1f}" y2="{bottom + 8:.1f}" stroke="{theme.BORDER}" '
                           'stroke-dasharray="3 5"/>')

    # --- liens (les étiquettes « +n j » sont posées ensuite, au-dessus des traits)
    si_labels = []
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
                           f'stroke="{col}" stroke-width="{sw}"{da} marker-end="url(#arr-{mk})"><title>{K.esc(val(c.lien))}</title></path>')
                si = links.serial_interval(n.case, c.case)
                if si is not None:
                    # au bout de la flèche, sur la ligne de l'enfant (deux enfants n'ont jamais la même ligne),
                    # sans déborder sur le cadre du parent
                    txt, size = _fit(trf("{n} j", n=f"{si:+d}"), x2 - 9 - (x1 + 3), 9.5, 800, 6.5)
                    si_labels.append(f'<text x="{x2 - 9:.1f}" y="{cy - 4:.1f}" text-anchor="end" font-size="{size:g}" '
                                     f'font-weight="800" fill="{col}">{K.esc(txt)}</text>')
    if si_labels:
        out.append('<g class="halo">' + "".join(si_labels) + '</g>')

    # --- nœuds
    for r in shown:
        for n in _component(r):
            x, y = pos[n.key]
            yt = y - node_h / 2
            if n.case is None:
                out.append(_source_box(x, yt, node_w, node_h, n.label))
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
            dead = c.issue == "Décès"
            l1, s1 = _fit(cas(c), node_w - 15 - (8 if dead else 0), 10.5 if small else 11.5, 800, 6.0)
            j0 = jour(f"J0 {c.debut_symptomes:%d/%m}" if c.debut_symptomes else "J0 ?")
            full2 = f"{c.zs or tr('ZS ?')} / {c.aire_sante or tr('AS ?')} • {j0}"
            tip = f"{cas(c)} : {val(c.maladie)} {val(c.statut)}, {tr('issue')} {val(c.issue)}"
            if small:
                out.append(f'<text x="{x + 11:.1f}" y="{y + s1 * 0.36:.1f}" font-size="{s1:g}" font-weight="800" fill="#fff">'
                           f'{K.esc(l1)}<title>{K.esc(tip + ", " + full2)}</title></text>')
            else:
                l2, s2 = _fit(full2, node_w - 18, 9.5, 400, 7.0)
                out.append(f'<text x="{x + 11:.1f}" y="{y - 3:.1f}" font-size="{s1:g}" font-weight="800" fill="#fff">'
                           f'{K.esc(l1)}<title>{K.esc(tip)}</title></text>')
                out.append(f'<text x="{x + 11:.1f}" y="{y + 12:.1f}" font-size="{s2:g}" fill="#fff" fill-opacity=".82">'
                           f'{K.esc(l2)}</text>')
            if dead:
                out.append(f'<text x="{x + node_w - 6:.1f}" y="{yt + min(13.0, node_h - 3):.1f}" text-anchor="end" font-size="10" '
                           f'font-weight="800" fill="#FF9C8F">†</text>')

    if not shown:
        msg = [tr("Aucun lien de transmission saisi."),
               tr("Dans chaque fiche (onglet Identité), renseignez « ID du cas source » :"),
               tr("l'ID (N° EPID) du cas dont ce cas est le contact.")]
        out.append(K.multiline(x0 + aw / 2, y0 + ah / 2 - 20, msg, 13, 600, theme.MUTED, lh=1.6))

    # --- légende
    out.append('<g class="legende">')
    for i, line in enumerate(leg_lines):
        for lx, item in line:
            out.append(_legend_svg(lx, leg_y + i * leg_lh, item))
    out.append('</g>')

    out.append(_panel(cases, ch, focus, hidden))
    out.append(K.footer(tr("Lien = ID du cas source saisi dans la fiche ; une « piste » (cas contagieux et cas exposé au même lieu) "
                           "oriente l'investigation mais n'établit pas la transmission.")))
    out.append("</svg>")
    return "".join(out)


def _source_box(x, yt, w, h, ident: str) -> str:
    """Source hors périmètre : cadre en tirets ; l'ID saisi reste lisible (2e ligne, ou seule ligne si le cadre est bas)."""
    tip = tr("Source hors périmètre") + " : " + (ident or "?")
    out = [f'<rect x="{x:.1f}" y="{yt:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" fill="#fff" '
           f'stroke="{theme.MUTED}" stroke-width="1.6" stroke-dasharray="4 3"><title>{K.esc(tip)}</title></rect>']
    tw, cx = w - 12, x + w / 2
    ident = ident or "?"
    one, s_one = _fit(ident, tw, 9.5, 800, 7.5)
    if h >= 30 and not one.endswith("…"):
        # deux lignes : « Source hors périmètre » puis l'ID entier, plus petit
        head, s1 = _fit(tr("Source hors périmètre"), tw, 9, 700, 6.5)
        gap = (h - s1 - s_one - 3) / 2
        out.append(_text(cx, yt + gap + s1 * 0.85, head, s1, 700, theme.MUTED, "middle"))
        out.append(_text(cx, yt + gap + s1 + 3 + s_one * 0.85, one, s_one, 800, theme.TEXT, "middle"))
        return "".join(out)
    if not one.endswith("…"):
        out.append(_text(cx, yt + h / 2 + s_one * 0.36, one, s_one, 800, theme.TEXT, "middle"))
        return "".join(out)
    # ID trop long pour une ligne : coupé aux tirets (ou n'importe où) sur autant de lignes que le cadre en contient
    for size in (8.5, 8.0, 7.5, 7.0, 6.5):
        n_max = max(1, int((h - 4) // (size * 1.15)))
        lines = _split_id(ident, tw, size, n_max)
        if lines:
            y = yt + (h - size * 1.15 * len(lines)) / 2 + size * 0.9
            for ln in lines:
                out.append(_text(cx, y, ln, size, 800, theme.TEXT, "middle"))
                y += size * 1.15
            return "".join(out)
    idl, s2 = _fit(ident, tw, 9.5, 800, 6.0)
    out.append(_text(cx, yt + h / 2 + s2 * 0.36, idl, s2, 800, theme.TEXT, "middle"))
    return "".join(out)


def _split_id(ident: str, max_w: float, size: float, n_max: int) -> List[str]:
    """Coupe un ID en lignes de max_w px, de préférence après un tiret ; [] s'il faut plus de n_max lignes."""
    lines, cur = [], ""
    for ch in ident:
        if cur and K.text_width(cur + ch, size, 800) > max_w:
            cut = cur.rfind("-") + 1
            if 0 < cut < len(cur):
                lines.append(cur[:cut])
                cur = cur[cut:]
            else:
                lines.append(cur)
                cur = ""
        cur += ch
    if cur:
        lines.append(cur)
    return lines if len(lines) <= n_max else []


def _panel(cases: List[Case], ch: "links.Chains", focus: Optional[Case], hidden: int) -> str:
    """Panneau de synthèse : chaque bloc avance ligne par ligne et s'arrête avant le bas du cadre."""
    X, TW = PANEL_X + 16, PANEL_TW
    out = ['<g class="panneau">', K.card(PANEL_X, 66, PANEL_W, 616), K.pill(PANEL_X + 12, 78, tr("Synthèse"))]
    y = 116.0

    def room(h: float) -> bool:
        return y + h <= PANEL_YMAX

    def para(text: str, size: float, weight: int, fill: str, max_lines: int = 2, lh: float = 1.3, after: float = 4):
        nonlocal y
        for ln in K.wrap_px(text, TW, size, weight, max_lines):
            if not room(0):
                return
            out.append(_text(X, y, ln, size, weight, fill))
            y += size * lh
        y += after

    case_nodes = [n for r in ch.roots for n in _component(r) if n.case]
    by_id = {c.id: c for c in cases}
    sis = [si for p, cid in ch.edges if (si := links.serial_interval(by_id.get(p), by_id.get(cid))) is not None]
    longest = max((max(n.gen for n in _component(r)) + 1 for r in ch.roots), default=0)
    stats = [trf("{n} cas dans le périmètre", n=len(cases)),
             trf("{c} chaîne(s) • {n} cas reliés", c=len(ch.roots), n=len(case_nodes)),
             trf("Chaîne la plus longue : {n} génération(s)", n=longest) if longest else tr("Aucune chaîne"),
             jour(trf("Intervalle moyen entre J0 : {m} j (n = {n})", m=f"{mean(sis):.1f}", n=len(sis)) if sis
                  else tr("Intervalle entre J0 : ? (dates manquantes)"))]
    for s in stats:
        para(s, 11.5, 700, theme.TEXT, after=4.5)
    if hidden:            # chaînes sans place à gauche : signalées ici, jamais par-dessus la légende
        para(trf("+ {n} autre(s) chaîne(s) non affichée(s) : filtrez par province / zone.", n=hidden),
             10.5, 700, theme.RED, after=4.5)

    y += 4
    out.append(K.pill(PANEL_X + 12, y, tr("Cas sans lien saisi")))
    y += 36
    if not ch.isolated:
        para(tr("Tous les cas sont rattachés."), 10.5, 400, theme.MUTED, 1, after=6)
    n_iso = 0
    for c in ch.isolated[:7]:
        if not room(16 + 70):                       # garder la place des pistes
            break
        j0 = jour(f"J0 {c.debut_symptomes:%d/%m}" if c.debut_symptomes else "J0 ?")
        rest = K.ellipsize(f" • {c.aire_sante or tr('AS ?')} • {j0}", TW * 0.45, 10.5)
        lab = K.ellipsize(cas_long(c), TW - K.text_width(rest, 10.5) - 2, 10.5, 800)
        out.append(f'<text x="{X}" y="{y:.1f}" font-size="10.5" fill="{theme.TEXT}"><tspan font-weight="800">'
                   f'{K.esc(lab)}</tspan>{K.esc(rest)}</text>')
        y += 16
        n_iso += 1
    if len(ch.isolated) > n_iso:
        para("… " + trf("et {n} autre(s)", n=len(ch.isolated) - n_iso), 10, 400, theme.MUTED, 1, after=0)
    y += 10

    # pistes : lieux communs entre cas non reliés
    linked = set(ch.edges) | {(b, a) for a, b in ch.edges}
    pistes = []
    for sp in links.shared_places(cases, focus):
        for a, b in sp.pistes:
            if (a.id, b.id) not in linked:
                pistes.append((sp.name, a, b))
    if room(36 + 14):
        out.append(K.pill(PANEL_X + 12, y, tr("Pistes : lieux communs")))
        y += 36
        if not pistes:
            para(tr("Aucune piste non reliée détectée."), 10.5, 400, theme.MUTED, 1, after=8)
        shown = 0
        for name, a, b in pistes[:6]:
            if not room(14 + 13):
                break
            out.append(_text(X, y, K.ellipsize(trf("{a} → {b} ?", a=cas(a), b=cas(b)), TW, 10.5, 800), 10.5, 800, theme.ORANGE))
            out.append(_text(X, y + 14, K.ellipsize(trf("à {lieu}", lieu=name), TW, 9.5), 9.5, 400, theme.MUTED))
            y += 32
            shown += 1
        if len(pistes) > shown and room(0):
            para("… " + trf("et {n} autre(s)", n=len(pistes) - shown), 9.5, 400, theme.MUTED, 1, after=4)

    # liens écartés (ID en double, boucle) : sous les pistes, chacun sur ses lignes, jamais par-dessus
    for msg in ch.ignored[:3]:
        if not room(12):
            break
        para(msg, 9, 400, theme.RED, 2, lh=1.25, after=3)
    out.append('</g>')
    return "".join(out)


def render_html(cases: List[Case], focus: Optional[Case] = None, zone: str = "") -> str:
    return render_svg_page(render_svg(cases, focus, zone), "Chaînes de transmission")
