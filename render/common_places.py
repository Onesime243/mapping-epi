"""Lieux communs : tableau lieux × cas.

Une ligne par lieu fréquenté par au moins deux cas, une colonne par cas. Chaque pastille indique
la date du passage et la période du cas à ce moment :
rouge = cas contagieux, bleu = dans sa fenêtre d'exposition, gris = autre période / date inconnue.
Un lieu où un cas contagieux et un cas exposé se sont succédé est signalé « transmission possible ».
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from config import theme
from core import links
from core.models import Case
from render import svgkit as K
from render.html_renderer import render_svg_page

PHASE_COLOR = {"contagieux": theme.RED, "exposition": theme.BLUE, "": "#9AA6B5"}
MAX_COLS, MAX_ROWS = 12, 12


def _fmt(v: links.Visit) -> str:
    if not v.debut:
        return "?"
    if v.fin and v.fin != v.debut:
        return f"{v.debut:%d/%m}–{v.fin:%d/%m}" if v.debut.month != v.fin.month else f"{v.debut:%d}–{v.fin:%d/%m}"
    return f"{v.debut:%d/%m}"


def render_svg(cases: List[Case], focus: Optional[Case] = None, zone: str = "") -> str:
    shared = links.shared_places(cases, focus)
    title = "LIEUX COMMUNS FRÉQUENTÉS PAR LES CAS" + (f" | {zone.upper()}" if zone else "")
    sub = ("Lieux partagés par la fiche ouverte et les autres cas" if focus else
           "Lieux fréquentés par au moins deux cas") + " • date du passage et période du cas à ce moment"
    out = [K.svg_open(), K.header(title, sub)]
    out.append(K.card(16, 66, 1248, 616))
    if not shared:
        msg = ["Aucun lieu commun entre les cas de votre périmètre.",
               "Les lieux sont comparés à partir de la chronologie (Lieu / Arrivée) et de l'onglet Lieux",
               "(casse, accents et précisions entre parenthèses ignorés)."]
        out.append(K.multiline(640, 340, msg, 13, 600, theme.MUTED, lh=1.6))
        out.append(K.footer("Un lieu commun n'établit pas un lien de transmission : il oriente l'investigation."))
        out.append("</svg>")
        return "".join(out)

    rows = shared[:MAX_ROWS]
    cols: List[Case] = []
    for sp in rows:
        for c in sp.cases:
            if c not in cols:
                cols.append(c)
    cols.sort(key=lambda c: (c.debut_symptomes or date.max, c.rang or 999))
    if focus and focus in cols:
        cols.remove(focus)
        cols.insert(0, focus)
    hidden_cols = max(0, len(cols) - MAX_COLS)
    cols = cols[:MAX_COLS]

    name_w, flag_w = 250, 236
    gx0 = 16 + 14 + name_w
    col_w = (1248 - 28 - name_w - flag_w) / max(1, len(cols))
    head_y = 82
    row_y0 = 140
    row_h = min(42.0, (600 - row_y0 + 40) / max(1, len(rows)))

    # en-têtes des cas
    for i, c in enumerate(cols):
        cx = gx0 + col_w * (i + 0.5)
        is_focus = focus is not None and c.id == focus.id
        if is_focus:
            out.append(f'<rect x="{gx0 + col_w * i + 2:.1f}" y="{head_y - 4}" width="{col_w - 4:.1f}" '
                       f'height="{row_y0 - head_y + len(rows) * row_h:.1f}" rx="7" fill="{theme.TEAL}" fill-opacity=".07" '
                       f'stroke="{theme.TEAL}" stroke-opacity=".5"/>')
        lines = [K.ellipsize(links.case_label(c), col_w - 8, 11.5, 800), (c.zs or "ZS ?")[:int(col_w / 6)],
                 f"J0 {c.debut_symptomes:%d/%m}" if c.debut_symptomes else "J0 ?"]
        out.append(f'<text x="{cx:.1f}" y="{head_y + 14}" text-anchor="middle" font-size="11.5" font-weight="800" '
                   f'fill="{theme.NAVY}">{K.esc(lines[0])}<title>{K.esc(links.case_long_label(c) + ", AS " + (c.aire_sante or "?"))}</title></text>')
        out.append(f'<text x="{cx:.1f}" y="{head_y + 29}" text-anchor="middle" font-size="9.5" fill="{theme.MUTED}">{K.esc(lines[1])}</text>')
        out.append(f'<text x="{cx:.1f}" y="{head_y + 43}" text-anchor="middle" font-size="9.5" font-weight="700" fill="{theme.TEXT}">{K.esc(lines[2])}</text>')
    out.append(f'<text x="30" y="{head_y + 29}" font-size="10" font-weight="800" fill="{theme.MUTED}" letter-spacing=".6">LIEU</text>')
    out.append(f'<text x="{1264 - 14 - flag_w + 10}" y="{head_y + 29}" font-size="10" font-weight="800" fill="{theme.MUTED}" '
               'letter-spacing=".6">LECTURE</text>')

    for r, sp in enumerate(rows):
        y = row_y0 + r * row_h
        cy = y + row_h / 2
        if r % 2 == 0:
            out.append(f'<rect x="24" y="{y:.1f}" width="1232" height="{row_h:.1f}" rx="5" fill="{theme.BG}"/>')
        nm = K.wrap(sp.name, 34, 1)[0]
        out.append(f'<text x="32" y="{cy - 2:.1f}" font-size="11.5" font-weight="800" fill="{theme.TEXT}">{K.esc(nm)}'
                   f'<title>{K.esc(sp.name)}</title></text>')
        out.append(f'<text x="32" y="{cy + 12:.1f}" font-size="9.5" fill="{theme.MUTED}">{len(sp.cases)} cas</text>')
        for i, c in enumerate(cols):
            vs = [v for v in sp.visits if v.case.id == c.id]
            if not vs:
                continue
            cx = gx0 + col_w * (i + 0.5)
            dated = [v for v in vs if v.debut]
            v = next((x for x in dated if x.phase == "contagieux"), None) or (dated[0] if dated else vs[0])
            col = PHASE_COLOR.get(v.phase, PHASE_COLOR[""])
            tip = "; ".join(f"{_fmt(x)} {x.quoi} ({x.phase or 'hors fenêtres'})" for x in vs)
            out.append(f'<circle cx="{cx:.1f}" cy="{cy - 6:.1f}" r="6.5" fill="{col}"><title>{K.esc(tip)}</title></circle>')
            lab = _fmt(v) + (f" +{len(vs) - 1}" if len(vs) > 1 else "")
            out.append(f'<text x="{cx:.1f}" y="{cy + 11:.1f}" text-anchor="middle" font-size="9" font-weight="700" '
                       f'fill="{theme.TEXT}">{K.esc(lab)}</text>')
        fx = 1264 - 14 - flag_w + 10
        if sp.pistes:
            a, b = sp.pistes[0]
            more = f" (+{len(sp.pistes) - 1})" if len(sp.pistes) > 1 else ""
            out.append(f'<text x="{fx}" y="{cy - 2:.1f}" font-size="10.5" font-weight="800" fill="{theme.RED}">'
                       f'⚠ Transmission possible{more}</text>')
            out.append(f'<text x="{fx}" y="{cy + 12:.1f}" font-size="9.5" fill="{theme.TEXT}">'
                       f'{K.esc(links.case_label(a))} contagieux → {K.esc(links.case_label(b))} exposé</text>')
        else:
            out.append(f'<text x="{fx}" y="{cy + 4:.1f}" font-size="10" fill="{theme.MUTED}">Lieu commun à vérifier</text>')

    ly = 662
    out.append(K.legend_item(32, ly, theme.RED, "Cas contagieux lors du passage", kind="circle"))
    out.append(K.legend_item(262, ly, theme.BLUE, "Dans sa fenêtre d'exposition", kind="circle"))
    out.append(K.legend_item(482, ly, "#9AA6B5", "Autre période / date inconnue", kind="circle"))
    extra = []
    if len(shared) > MAX_ROWS:
        extra.append(f"+ {len(shared) - MAX_ROWS} lieu(x)")
    if hidden_cols:
        extra.append(f"+ {hidden_cols} cas")
    if extra:
        out.append(f'<text x="1248" y="{ly + 4}" text-anchor="end" font-size="10" font-weight="700" fill="{theme.RED}">'
                   f'{K.esc(" • ".join(extra))} non affichés : filtrez par zone</text>')
    n_pistes = sum(1 for s in shared if s.pistes)
    out.append(K.footer(f"{len(shared)} lieu(x) commun(s) • {n_pistes} avec transmission possible. Comparaison sur le nom du lieu "
                        "(casse et accents ignorés). Un lieu commun oriente l'investigation, il ne prouve pas la transmission."))
    out.append("</svg>")
    return "".join(out)


def render_html(cases: List[Case], focus: Optional[Case] = None, zone: str = "") -> str:
    return render_svg_page(render_svg(cases, focus, zone), "Lieux communs")
